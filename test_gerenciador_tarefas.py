import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import logging # <-- Importa o módulo logging

# Importa as classes e a exceção Error do seu script principal
from gerenciador_tarefas import BancoDeDados, Tarefa, GerenciadorTarefas, CONFIG_BANCO
from mysql.connector import Error # <-- Importa a exceção Error

# --- Fixtures para Mocking ---

@pytest.fixture
def mock_mysql_connector_connect(mocker):
    """
    Fixture para mockar mysql.connector.connect.
    Retorna o mock do objeto da função connect.
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Configura o mock_conn para retornar um mock_cursor quando .cursor() for chamado
    mock_conn.cursor.return_value = mock_cursor
    # Configura .is_connected() para retornar True por padrão
    mock_conn.is_connected.return_value = True
    # Configura .commit() para não fazer nada, apenas registrar a chamada
    mock_conn.commit.return_value = None

    # Mocka a função connect do mysql.connector e armazena o mock retornado
    mock_connect_func = mocker.patch('mysql.connector.connect', return_value=mock_conn)
    
    # Adiciona o mock_cursor ao mock_connect_func para fácil acesso nos testes
    mock_connect_func.mock_cursor = mock_cursor 
    mock_connect_func.mock_conn = mock_conn

    return mock_connect_func # Retorna o mock da função connect

@pytest.fixture
def banco_de_dados_com_mock_conexao(mocker):
    """
    Fixture para criar uma instância de BancoDeDados com mocks de conexão e cursor.
    Usada para testar métodos da própria classe BancoDeDados.
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.is_connected.return_value = True

    # Mocka mysql.connector.connect para que BancoDeDados use os mocks
    mocker.patch('mysql.connector.connect', return_value=mock_conn)

    # Cria uma instância real de BancoDeDados que agora usará os mocks
    bd = BancoDeDados(config=CONFIG_BANCO)
    
    # Reseta os mocks para garantir um estado limpo para cada teste
    # (O __init__ de BancoDeDados já chamou conectar e criar_tabela)
    mock_conn.reset_mock()
    mock_cursor.reset_mock()
    mock_conn.is_connected.return_value = True # Garante que a conexão está ativa para o teste

    # Adiciona os mocks diretamente à instância bd para fácil acesso nos testes
    bd.conexao = mock_conn
    bd.cursor = mock_cursor

    return bd

@pytest.fixture
def gerenciador_com_mock_bd(mock_mysql_connector_connect, mocker): # Adicionado 'mocker' aqui
    """
    Fixture para criar uma instância de GerenciadorTarefas com um BancoDeDados que usa mocks.
    Mocka os métodos executar_comando e buscar_dados na instância bd.
    """
    # A instância de BancoDeDados será criada e usará o mysql.connector.connect mockado
    gerenciador = GerenciadorTarefas()

    # Resetar os mocks da conexão e cursor APÓS a inicialização do BancoDeDados
    # para que os testes de GerenciadorTarefas comecem com um histórico limpo.
    mock_mysql_connector_connect.mock_conn.reset_mock()
    mock_mysql_connector_connect.mock_cursor.reset_mock()
    mock_mysql_connector_connect.mock_conn.is_connected.return_value = True

    # Patch os métodos executar_comando e buscar_dados na instância bd
    # Isso garante que bd.executar_comando e bd.buscar_dados sejam mocks
    mocker.patch.object(gerenciador.bd, 'executar_comando', autospec=True)
    mocker.patch.object(gerenciador.bd, 'buscar_dados', autospec=True)

    return gerenciador

# --- Testes para a Classe BancoDeDados ---

def test_banco_de_dados_conexao_sucesso(mock_mysql_connector_connect):
    """
    Testa se a conexão com o banco de dados é estabelecida com sucesso.
    """
    bd = BancoDeDados(config=CONFIG_BANCO)
    mock_mysql_connector_connect.assert_called_once_with(**CONFIG_BANCO)
    assert bd.conexao is not None
    assert bd.cursor is not None
    mock_mysql_connector_connect.mock_conn.is_connected.assert_called()

def test_banco_de_dados_conexao_falha(mocker):
    """
    Testa o comportamento quando a conexão com o banco de dados falha.
    """
    mocker.patch('mysql.connector.connect', side_effect=Error("Erro de conexão simulado"))
    bd = BancoDeDados(config=CONFIG_BANCO)
    assert bd.conexao is None
    assert bd.cursor is None

def test_banco_de_dados_criar_tabela(banco_de_dados_com_mock_conexao): # Usa a nova fixture
    """
    Testa se o comando de criação de tabela é executado.
    """
    bd = banco_de_dados_com_mock_conexao # Pega a instância mockada de BancoDeDados
    
    bd.criar_tabela()
    
    bd.cursor.execute.assert_called_once_with(pytest.approx('''
                CREATE TABLE IF NOT EXISTS tarefas(
                    id INT AUTO_INCREMENT PRIMARY KEY, 
                    titulo VARCHAR(100) NOT NULL,
                    descricao TEXT,
                    responsavel VARCHAR(50),
                    status VARCHAR(20),
                    data_criacao DATETIME,
                    data_conclusao DATETIME
                )
            ''', abs=100))
    bd.conexao.commit.assert_called_once()

def test_banco_de_dados_fechar_conexao(banco_de_dados_com_mock_conexao): # Usa a nova fixture
    """
    Testa se a conexão e o cursor são fechados corretamente.
    """
    bd = banco_de_dados_com_mock_conexao
    bd.fechar_conexao()
    bd.cursor.close.assert_called_once()
    bd.conexao.close.assert_called_once()

def test_banco_de_dados_executar_comando(banco_de_dados_com_mock_conexao): # Usa a nova fixture
    """
    Testa a execução de um comando SQL genérico.
    """
    bd = banco_de_dados_com_mock_conexao
    
    comando = "INSERT INTO teste (col) VALUES (%s)"
    parametros = ("valor",)
    
    bd.executar_comando(comando, parametros)
    
    bd.cursor.execute.assert_called_once_with(comando, parametros)
    bd.conexao.commit.assert_called_once()

def test_banco_de_dados_buscar_dados(banco_de_dados_com_mock_conexao): # Usa a nova fixture
    """
    Testa a busca de dados no banco.
    """
    bd = banco_de_dados_com_mock_conexao
    dados_mock = [("1", "Tarefa Teste", "Desc", "Responsavel", "Pendente", datetime.now(), None)]
    bd.cursor.fetchall.return_value = dados_mock 
    
    comando = "SELECT * FROM tarefas"
    resultado = bd.buscar_dados(comando)
    
    bd.cursor.execute.assert_called_once_with(comando, ())
    assert resultado == dados_mock

# --- Testes para a Classe Tarefa ---

def test_tarefa_inicializacao():
    """
    Testa a inicialização de um objeto Tarefa.
    """
    titulo = "Minha Tarefa de Teste"
    descricao = "Esta é uma descrição."
    responsavel = "João"
    
    tarefa = Tarefa(titulo, descricao, responsavel)
    
    assert tarefa.titulo == titulo
    assert tarefa.descricao == descricao
    assert tarefa.responsavel == responsavel
    assert tarefa.status == "Pendente"
    assert isinstance(tarefa.data_criacao, datetime)
    assert tarefa.data_conclusao is None

# --- Testes para a Classe GerenciadorTarefas ---

def test_gerenciador_cadastrar_tarefa(gerenciador_com_mock_bd, monkeypatch):
    """
    Testa o cadastro de uma nova tarefa.
    """
    # Simula as entradas do usuário
    monkeypatch.setattr('builtins.input', lambda x: {
        "Título da tarefa: ": "Titulo da Tarefa de Teste",
        "Descrição da tarefa: ": "Descricao da tarefa",
        "Responsável: ": "Responsavel da tarefa"
    }[x])

    gerenciador_com_mock_bd.cadastrar_tarefa()
    
    # Verifica se o método executar_comando foi chamado no mock do método
    gerenciador_com_mock_bd.bd.executar_comando.assert_called_once()
    args, kwargs = gerenciador_com_mock_bd.bd.executar_comando.call_args
    assert "INSERT INTO tarefas" in args[0]
    assert "Titulo da Tarefa de Teste" in args[1]
    assert "Descricao da tarefa" in args[1]
    assert "Responsavel da tarefa" in args[1]
    assert "Pendente" in args[1]


def test_gerenciador_exibir_tarefas_vazio(gerenciador_com_mock_bd):
    """
    Testa a exibição de tarefas quando não há nenhuma cadastrada.
    """
    # Configura o mock do método buscar_dados para retornar uma lista vazia
    gerenciador_com_mock_bd.bd.buscar_dados.return_value = []
    gerenciador_com_mock_bd.exibir_tarefas()
    # Verifica se buscar_dados foi chamado
    gerenciador_com_mock_bd.bd.buscar_dados.assert_called_once_with("SELECT * FROM tarefas")

def test_gerenciador_exibir_tarefas_com_dados(gerenciador_com_mock_bd, caplog):
    """
    Testa a exibição de tarefas com dados.
    """
    data_criacao_mock = datetime(2023, 1, 1, 10, 0, 0)
    data_conclusao_mock = datetime(2023, 1, 2, 11, 0, 0)
    tarefas_mock = [
        (1, "Tarefa 1", "Desc 1", "Resp 1", "Pendente", data_criacao_mock, None),
        (2, "Tarefa 2", "Desc 2", "Resp 2", "Concluída", data_criacao_mock, data_conclusao_mock)
    ]
    # Configura o mock do método buscar_dados para retornar os dados mockados
    gerenciador_com_mock_bd.bd.buscar_dados.return_value = tarefas_mock
    
    # Captura os logs para verificar a saída
    with caplog.at_level(logging.INFO):
        gerenciador_com_mock_bd.exibir_tarefas()
    
    assert "ID: 1" in caplog.text
    assert "Título: Tarefa 1" in caplog.text
    assert "Status: Pendente" in caplog.text
    assert "Data de Conclusão: Não concluída" in caplog.text
    assert "ID: 2" in caplog.text
    assert "Status: Concluída" in caplog.text
    assert f"Data de Conclusão: {data_conclusao_mock}" in caplog.text


def test_gerenciador_atualizar_tarefa_sucesso(gerenciador_com_mock_bd, monkeypatch):
    """
    Testa a atualização de uma tarefa com novos dados.
    """
    # Resetar mocks para este teste específico
    gerenciador_com_mock_bd.bd.executar_comando.reset_mock()
    gerenciador_com_mock_bd.bd.buscar_dados.reset_mock()

    # Um exemplo de tarefa completa para o mock de exibir_tarefas e dados atuais
    sample_full_task_for_display = (1, "Titulo Antigo", "Desc Antiga", "Resp Antigo", "Pendente", datetime(2023, 1, 1), None)

    # Configura o mock do método buscar_dados para simular os retornos em ordem
    gerenciador_com_mock_bd.bd.buscar_dados.side_effect = [
        [sample_full_task_for_display], # 1ª chamada: para exibir_tarefas (SELECT *)
        [(1,)], # 2ª chamada: para verificar tarefas_existentes (SELECT id)
        [("Titulo Antigo", "Desc Antiga", "Resp Antigo", "Pendente", None)] # 3ª chamada: para dados_atuais (SELECT titulo, descricao, ...)
    ]

    # Simula as entradas do usuário
    monkeypatch.setattr('builtins.input', lambda x: {
        "Digite o ID da tarefa que deseja atualizar: ": "1",
        "Novo Título (atual: Titulo Antigo): ": "Novo Titulo",
        "Nova Descrição (atual: Desc Antiga): ": "Nova Descricao",
        "Novo Responsável (atual: Resp Antigo): ": "Novo Responsavel",
        "Novo Status (atual: Pendente) (Pendente, Em Andamento, Concluída): ": "Em Andamento"
    }[x])

    gerenciador_com_mock_bd.atualizar_tarefa()

    # Verifica se o comando UPDATE foi chamado corretamente no mock do método
    gerenciador_com_mock_bd.bd.executar_comando.assert_called_once()
    args, kwargs = gerenciador_com_mock_bd.bd.executar_comando.call_args
    assert "UPDATE tarefas SET titulo=%s, descricao=%s, responsavel=%s, status=%s, data_conclusao=%s WHERE id=%s" in args[0]
    assert args[1][0] == "Novo Titulo"
    assert args[1][1] == "Nova Descricao"
    assert args[1][2] == "Novo Responsavel"
    assert args[1][3] == "Em Andamento"
    assert args[1][4] is None # Data de conclusão deve ser None se não for "Concluída"
    assert args[1][5] == "1"

def test_gerenciador_atualizar_tarefa_para_concluida(gerenciador_com_mock_bd, monkeypatch):
    """
    Testa a atualização de uma tarefa para status 'Concluída', verificando a data de conclusão.
    """
    # Resetar mocks para este teste específico
    gerenciador_com_mock_bd.bd.executar_comando.reset_mock()
    gerenciador_com_mock_bd.bd.buscar_dados.reset_mock()

    # Um exemplo de tarefa completa para o mock de exibir_tarefas
    sample_full_task_for_display = (1, "Titulo Antigo", "Desc Antiga", "Resp Antigo", "Pendente", datetime(2023, 1, 1), None)

    # Configura o mock do método buscar_dados para simular os retornos
    gerenciador_com_mock_bd.bd.buscar_dados.side_effect = [
        [sample_full_task_for_display], # 1ª chamada: para exibir_tarefas (SELECT *)
        [(1,)], # 2ª chamada: para verificar tarefas_existentes (SELECT id)
        [("Titulo Antigo", "Desc Antiga", "Resp Antigo", "Pendente", None)] # 3ª chamada: para dados_atuais (SELECT titulo, descricao, ...)
    ]

    # Simula as entradas do usuário
    monkeypatch.setattr('builtins.input', lambda x: {
        "Digite o ID da tarefa que deseja atualizar: ": "1",
        "Novo Título (atual: Titulo Antigo): ": "", # Manter antigo
        "Nova Descrição (atual: Desc Antiga): ": "", # Manter antigo
        "Novo Responsável (atual: Resp Antigo): ": "", # Manter antigo
        "Novo Status (atual: Pendente) (Pendente, Em Andamento, Concluída): ": "Concluída"
    }[x])

    # Mocka datetime.now() para ter um valor fixo durante o teste
    with patch('gerenciador_tarefas.datetime') as mock_dt:
        mock_dt.now.return_value = datetime(2024, 7, 11, 10, 30, 0)
        # Garante que outras chamadas como datetime.strptime funcionem se usadas
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw) 
        mock_dt.strptime = datetime.strptime 

        gerenciador_com_mock_bd.atualizar_tarefa()

        # Verifica se o comando UPDATE foi chamado corretamente
        gerenciador_com_mock_bd.bd.executar_comando.assert_called_once()
        args, kwargs = gerenciador_com_mock_bd.bd.executar_comando.call_args
        assert args[1][3] == "Concluída"
        assert args[1][4] == datetime(2024, 7, 11, 10, 30, 0) # Deve ser a data mockada

def test_gerenciador_atualizar_tarefa_de_concluida_para_pendente(gerenciador_com_mock_bd, monkeypatch):
    """
    Testa a atualização de uma tarefa de 'Concluída' para 'Pendente', verificando a data de conclusão.
    """
    # Resetar mocks para este teste específico
    gerenciador_com_mock_bd.bd.executar_comando.reset_mock()
    gerenciador_com_mock_bd.bd.buscar_dados.reset_mock()

    data_conclusao_antiga = datetime(2023, 5, 10, 15, 0, 0)
    # Um exemplo de tarefa completa para o mock de exibir_tarefas
    sample_full_task_for_display = (1, "Titulo Antigo", "Desc Antiga", "Resp Antigo", "Concluída", datetime(2023, 1, 1), data_conclusao_antiga)

    # Simula que existe uma tarefa com ID 1
    gerenciador_com_mock_bd.bd.buscar_dados.side_effect = [
        [sample_full_task_for_display], # 1ª chamada: para exibir_tarefas (SELECT *)
        [(1,)], # 2ª chamada: para verificar tarefas_existentes (SELECT id)
        [("Titulo Antigo", "Desc Antiga", "Resp Antigo", "Concluída", data_conclusao_antiga)] # 3ª chamada: para dados_atuais
    ]

    # Simula as entradas do usuário
    monkeypatch.setattr('builtins.input', lambda x: {
        "Digite o ID da tarefa que deseja atualizar: ": "1",
        "Novo Título (atual: Titulo Antigo): ": "",
        "Nova Descrição (atual: Desc Antiga): ": "",
        "Novo Responsável (atual: Resp Antigo): ": "",
        "Novo Status (atual: Concluída) (Pendente, Em Andamento, Concluída): ": "Pendente"
    }[x])

    gerenciador_com_mock_bd.atualizar_tarefa()

    # Verifica se o comando UPDATE foi chamado corretamente
    gerenciador_com_mock_bd.bd.executar_comando.assert_called_once()
    args, kwargs = gerenciador_com_mock_bd.bd.executar_comando.call_args
    assert args[1][3] == "Pendente"
    assert args[1][4] is None # Data de conclusão deve ser None

def test_gerenciador_excluir_tarefa_sucesso(gerenciador_com_mock_bd, monkeypatch):
    """
    Testa a exclusão de uma tarefa com sucesso.
    """
    # Resetar mocks para este teste específico
    gerenciador_com_mock_bd.bd.executar_comando.reset_mock()
    gerenciador_com_mock_bd.bd.buscar_dados.reset_mock()

    # Um exemplo de tarefa completa para o mock de exibir_tarefas
    sample_full_task_for_display = (1, "Tarefa a Excluir", "Desc", "Resp", "Pendente", datetime(2023, 1, 1), None)

    # Simula que existe uma tarefa com ID 1
    gerenciador_com_mock_bd.bd.buscar_dados.side_effect = [
        [sample_full_task_for_display], # 1ª chamada: para exibir_tarefas (SELECT *)
        [(1,)], # 2ª chamada: para verificar tarefas_existentes (SELECT id)
    ]

    # Simula a entrada do usuário
    monkeypatch.setattr('builtins.input', lambda x: "1")

    gerenciador_com_mock_bd.excluir_tarefa()

    # Verifica se o comando DELETE foi chamado no mock do método
    gerenciador_com_mock_bd.bd.executar_comando.assert_called_once_with("DELETE FROM tarefas WHERE id=%s", ("1",))

def test_gerenciador_excluir_tarefa_id_nao_encontrado(gerenciador_com_mock_bd, monkeypatch, caplog):
    """
    Testa a exclusão de uma tarefa com ID não encontrado.
    """
    # Resetar mocks para este teste específico
    gerenciador_com_mock_bd.bd.executar_comando.reset_mock()
    gerenciador_com_mock_bd.bd.buscar_dados.reset_mock()

    # Um exemplo de tarefa completa para o mock de exibir_tarefas
    sample_full_task_for_display = (1, "Tarefa Existente", "Desc", "Resp", "Pendente", datetime(2023, 1, 1), None)

    # Simula que existe uma tarefa com ID 1
    gerenciador_com_mock_bd.bd.buscar_dados.side_effect = [
        [sample_full_task_for_display], # 1ª chamada: para exibir_tarefas (SELECT *)
        [(1,)], # 2ª chamada: para verificar tarefas_existentes (SELECT id)
    ]

    # Simula a entrada do usuário com um ID inexistente
    monkeypatch.setattr('builtins.input', lambda x: "99")

    with caplog.at_level(logging.WARNING):
        gerenciador_com_mock_bd.excluir_tarefa()
    
    assert "Tarefa com ID 99 não encontrada." in caplog.text
    # Verifica que o comando DELETE NÃO foi chamado no mock do método
    gerenciador_com_mock_bd.bd.executar_comando.assert_not_called()

def test_gerenciador_fechar_sistema(gerenciador_com_mock_bd):
    """
    Testa se o sistema fecha a conexão com o banco de dados.
    """
    # O mock da conexão e do cursor já estão configurados para serem MagicMock
    # e fechar_conexao chama .close() neles.
    gerenciador_com_mock_bd.fechar_sistema()
    
    # Asserimos que os métodos close() dos mocks foram chamados
    gerenciador_com_mock_bd.bd.conexao.close.assert_called_once()
    gerenciador_com_mock_bd.bd.cursor.close.assert_called_once()



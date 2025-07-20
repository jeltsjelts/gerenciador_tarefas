import mysql.connector
from mysql.connector import Error
from datetime import datetime
import logging


# --- Configuração de Logging ---
# Configura o logger para exibir mensagens no console
# Níveis de logging: DEBUG, INFO, WARNING, ERROR, CRITICAL
# Alterado o nível para WARNING para ocultar mensagens INFO e DEBUG por padrão no console.
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_BANCO = {
    "host": "localhost",
    "user": "root",
    "password": <insert>,
    "database": <create>,
    "raise_on_warnings": True
}

#classe responsável pela conexão com o Banco de dados
class BancoDeDados:
    def __init__(self, config=CONFIG_BANCO):
        #configurar o banco de dados mariadb
        self.config = config
        self.conexao = None
        self.cursor = None
        self._conectar() # Tenta conectar no construtor
        

    def _conectar(self):    
        #Tenta estabelecer a conexão com o banco de dados.
        #Método interno para ser chamado no __init__ e em outras verificações.
        
        try:
            self.conexao = mysql.connector.connect(**self.config)
            if self.conexao.is_connected(): #verifica se a conexão foi bem sucedida
                self.cursor = self.conexao.cursor()
                logging.info("Conexão com o MariaDB estabelecida com sucesso!")
                self.criar_tabela()
            else:
                logging.warning("Não foi possível conectar ao MariaDB!")
        except Error as e:
            #foi atribuído umm alias para o erro de conexão
            logging.error(f"Erro ao conectar ao MariaDB: {e}")
            self.conexao = None
            self.cursor = None

    def criar_tabela(self):
        if not self.conexao or not self.conexao.is_connected():
            logging.warning("Não há conexão ativa com o banco de dados para criar a tabela!")
            return
        
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS tarefas(
                    id INT AUTO_INCREMENT PRIMARY KEY, 
                    titulo VARCHAR(100) NOT NULL,
                    descricao TEXT,
                    responsavel VARCHAR(50),
                    status VARCHAR(20),
                    data_criacao DATETIME,
                    data_conclusao DATETIME
                )
            ''')
            self.conexao.commit()
            logging.info("Tabela criada ou já existente.")
        except Error as e:
            # Verifica se o erro é porque a tabela já existe (código de erro 1050)
            if e.errno == 1050:
                logging.info(f"Tabela 'tarefas' já existe. ({e})")
            else:
                logging.error(f"Erro ao criar a tabela: {e}")

    def fechar_conexao(self):
        #método para fechar a conexao
        if self.conexao and self.conexao.is_connected():
            if self.cursor:
                self.cursor.close()
            self.conexao.close()
            logging.info("Conexão com o banco de dados fechada.")
        else:
            logging.info("Nenhuma conexão ativa para fechar.")
        
        
    def executar_comando(self, comando, parametros=()): #executa comandos SQL no banco de dados (INSERT, UPDATE, DELETE).
        if not self.conexao or not self.conexao.is_connected() or not self.cursor:
            logging.error("Erro: Não há conexão ativa com o banco de dados para executar o comando.")
            return
        try:
            self.cursor.execute(comando, parametros)
            self.conexao.commit()
        except Error as e:
            logging.error(f"Erro ao executar comando '{comando}' : {e}")
        
        
    def buscar_dados(self, comando, parametros=()): #executa comandos SQL no banco de dados para buscar os dados do banco
        if not self.conexao or not self.conexao.is_connected() or not self.cursor:
            logging.error("Erro: Não há conexão ativa com o banco de dados para buscar dados.")
            return []
        
        try:
            self.cursor.execute(comando, parametros)
            dados = self.cursor.fetchall()
            logging.debug(f"Dados buscados com sucesso: {comando} com {parametros}")
            return dados
        except Error as e:
            logging.error(f"Erro ao buscar os dados com o comando '{comando}' com parâmetros {parametros}: {e}")
            return []
        
#classe tarefa representa as informações da tarefa
class Tarefa:
    def __init__(self, titulo, descricao, responsavel):
        self.titulo = titulo
        self.descricao = descricao
        self.responsavel = responsavel
        self.status = "Pendente"
        self.data_criacao = datetime.now()
        self.data_conclusao = None
        
        
#classe gerenciar
class GerenciadorTarefas:
    def __init__(self):
        #chamada do banco de dados
        self.bd = BancoDeDados()

        #Verificar se a conexão foi bem sucedida
        
        if not self.is_bd_ready():
            logging.critical("Não foi possível inicializar o gerenciador de tarefas devido a um problema de conexão com o banco de dados!")
            self.bd = None #Define bd como None para evitar operações futuras
    
    
    def is_bd_ready(self):
        #Verifica se a instância do BancoDeDados e a conexão estão ativas
        return self.bd and self.bd.conexao and self.bd.conexao.is_connected()

        
    #métodos visíveis    
    def cadastrar_tarefa(self):
        if not self.is_bd_ready():
            logging.error("Não é possível cadastrar tarefa. A conexão com o banco de dados não está ativa!")
            return
        
        while True:
            titulo = input("Título da tarefa: ")
            if len(titulo) >= 12:
                break
            else: 
                logging.warning("Título da tarefa deve ser maior que 12 caracteres.")
                
        descricao = input("Descrição da tarefa: ")
        responsavel = input("Responsável: ")

        tarefa = Tarefa(titulo, descricao, responsavel)

        self.bd.executar_comando('''
            INSERT INTO tarefas (titulo, descricao, responsavel, status, data_criacao, data_conclusao)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (tarefa.titulo, tarefa.descricao, tarefa.responsavel, tarefa.status, tarefa.data_criacao, tarefa.data_conclusao))
        logging.info("Tarefa cadastrada com sucesso!")
    
    def exibir_tarefas(self):
        #exibir todas as tarefas cadastradas
        if not self.is_bd_ready():
            logging.error("Não é possível exibir tarefas. Conexão com o banco de dados não está ativa.")
            return
        
        tarefas = self.bd.buscar_dados("SELECT * FROM tarefas")
        #if para caso não exista tarefas cadastradas
        if not tarefas:
            logging.info("Nenhuma tarefa cadastrada.")
            return
        
        logging.info("\n --- Lista de Tarefas ---") # Alterado de print para logging.info
        #loop para exibir verticalmente
        for t in tarefas:
            logging.info(f"ID: {t[0]}")
            logging.info(f"Título: {t[1]}")
            logging.info(f"Descrição: {t[2]}")
            logging.info(f"Responsável: {t[3]}")
            logging.info(f"Status: {t[4]}")
            logging.info(f"Data da Criação: {t[5]}")
            logging.info(f"Data de Conclusão: {t[6] if t[6] else 'Não concluída'}\n") # Ajustado para exibir "Não concluída"

    def atualizar_tarefa(self):
        #atualizar as tarefas
        
        if not self.is_bd_ready():
            logging.error("Não é possível atualizar tarefa. Conexão com o banco de dados não está ativa.")
            return
        
        
        self.exibir_tarefas()
        tarefas_existentes = self.bd.buscar_dados("SELECT id FROM tarefas")
        if not tarefas_existentes:
            logging.info("Nenhuma tarefa cadastrada para atualizar.")
            return
                
        
        id_tarefa = input("Digite o ID da tarefa que deseja atualizar: ")

        tarefa_encontrada = False
        for t_id in tarefas_existentes:
            if str(t_id[0]) == id_tarefa:
                tarefa_encontrada = True
                break
        
        if not tarefa_encontrada:
            logging.warning(f"Tarefa com ID {id_tarefa} não encontrada.")
            return
        
        # Busca os dados atuais da tarefa para preencher como padrão
        dados_atuais = self.bd.buscar_dados("SELECT titulo, descricao, responsavel, status, data_conclusao FROM tarefas WHERE id=%s", (id_tarefa,))
        if not dados_atuais:
            logging.error("Erro ao buscar dados da tarefa para atualização.")
            return
        
        titulo_atual, descricao_atual, responsavel_atual, status_atual, data_conclusao_atual = dados_atuais[0]

        logging.info(f"\n--- Atualizando Tarefa ID: {id_tarefa} ---")
        logging.info("Deixe em branco para manter o valor atual.")

        novo_titulo = input(f"Novo Título (atual: {titulo_atual}): ")
        if not novo_titulo:
            novo_titulo = titulo_atual

        nova_descricao = input(f"Nova Descrição (atual: {descricao_atual}): ")
        if not nova_descricao:
            nova_descricao = descricao_atual

        novo_responsavel = input(f"Novo Responsável (atual: {responsavel_atual}): ")
        if not novo_responsavel:
            novo_responsavel = responsavel_atual

        novo_status = input(f"Novo Status (atual: {status_atual}) (Pendente, Em Andamento, Concluída): ")
        if not novo_status:
            novo_status = status_atual
        
        # Lógica para data_conclusao: se o novo status for "Concluída", atualiza a data
        # Caso contrário, mantém a data de conclusão atual (ou None)
        data_conclusao = data_conclusao_atual
        if novo_status.lower() == "concluída" and (status_atual is None or status_atual.lower() != "concluída"):
            data_conclusao = datetime.now()
        elif novo_status.lower() != "concluída" and (status_atual is not None and status_atual.lower() == "concluída"):
            # Se o status mudou de concluída para outro, a data de conclusão é removida
            data_conclusao = None
        
        self.bd.executar_comando('''
            UPDATE tarefas SET titulo=%s, descricao=%s, responsavel=%s, status=%s, data_conclusao=%s WHERE id=%s
        ''', (novo_titulo, nova_descricao, novo_responsavel, novo_status, data_conclusao, id_tarefa))
        logging.info("Tarefa atualizada com sucesso!") 

    def excluir_tarefa(self):
        if not self.is_bd_ready():
            logging.error("Não é possível excluir tarefa. Conexão com o banco de dados não está ativa.")
            return
        
        self.exibir_tarefas()
        tarefas_existentes = self.bd.buscar_dados("SELECT id FROM tarefas")
        if not tarefas_existentes:
            logging.info("Nenhuma tarefa cadastrada para excluir.")
            return
        
        #excluir uma tarefa
        id_tarefa = input("Digite a ID para excluir uma tarefa: ")

        #Verificar se o ID da tarefa existe
        tarefa_encontrada = False
        for t_id in tarefas_existentes:
            if str(t_id[0]) == id_tarefa:
                tarefa_encontrada = True
                break
        
        if not tarefa_encontrada:
            logging.warning(f"Tarefa com ID {id_tarefa} não encontrada.")
            return
        
        self.bd.executar_comando('''DELETE FROM tarefas WHERE id=%s''', (id_tarefa,))
        logging.info("Tarefa excluída com sucesso!")

    def fechar_sistema(self):
        if self.bd:
            self.bd.fechar_conexao()
        logging.info("Sistema encerrado")

def main():
    gerenciador = GerenciadorTarefas()
    #se o gerenciador não conseguiu se conectar ao BD, encerra o programa
    if not gerenciador.is_bd_ready():
        logging.critical("Encerrando o programa devido a falha na conexão com o Banco de dados!")
        return

    while True:
        # Estas mensagens são importantes para a interação do usuário e devem ser sempre visíveis.
        # Por isso, usamos print() em vez de logging.info() aqui.
        print("\n--- Gestão de Tarefas ---")
        print("1 - Cadastrar Tarefa")
        print("2 - Exibir Tarefas")
        print("3 - Atualizar Tarefa")
        print("4 - Excluir Tarefa")
        print("5 - Sair do Sistema")
        
        try:
            arg = int(input("Escolha uma opção: "))
            match arg:
                case 1:
                    gerenciador.cadastrar_tarefa()
                case 2:
                    gerenciador.exibir_tarefas()
                case 3:
                    gerenciador.atualizar_tarefa()
                case 4:
                    gerenciador.excluir_tarefa()
                case 5:
                    gerenciador.fechar_sistema()
                    break # Sai do loop quando o sistema é encerrado
                case _:
                    logging.warning("Opção não encontrada! Tente novamente!")
        except ValueError:
            logging.error("Entrada inválida. Por favor, digite um número inteiro.")
        except Exception as e:
            logging.critical(f"Ocorreu um erro inesperado: {e}", exc_info=True) # exc_info=True para logar o traceback
            gerenciador.fechar_sistema() # Tenta fechar a conexão em caso de erro crítico
            break
                    
if __name__=="__main__":
    main()



            



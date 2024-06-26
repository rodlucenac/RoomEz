import streamlit as st
from banco import conectar
import bcrypt
from datetime import date
import threading
import time
from email_send import send_email

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_type' not in st.session_state:
    st.session_state['user_type'] = None
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'Home'

def show_home():
    st.title("Página Inicial - Escolha um Hotel")
    
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT cidade FROM Hoteis")
    cidades = [cidade[0] for cidade in cursor.fetchall()]
    cursor.close()

    cidade_escolhida = st.selectbox("Selecione a cidade", ["Todas"] + cidades)

    criterio_ordem = st.selectbox("Ordenar por", ["Preço (Menor para Maior)", "Preço (Maior para Menor)", "Rating (Maior para Menor)", "Rating (Menor para Maior)"])

    query = "SELECT Hotel_id, nome, cidade FROM Hoteis"
    params = []

    if cidade_escolhida != "Todas":
        query += " WHERE cidade = %s"
        params.append(cidade_escolhida)

    if "Preço" in criterio_ordem:
        query += " ORDER BY preco"
        if "Maior para Menor" in criterio_ordem:
            query += " DESC"
    elif "Rating" in criterio_ordem:
        query += " ORDER BY rating"
        if "Menor para Maior" in criterio_ordem:
            query += " ASC"

    cursor = conn.cursor()
    cursor.execute(query, params)
    hoteis = cursor.fetchall()
    cursor.close()
    conn.close()

    for hotel in hoteis:
        if st.button(f"Ver detalhes de {hotel[1]}", key=hotel[0]):
            st.session_state['current_hotel_id'] = hotel[0]
            st.session_state['current_page'] = "Hotel"
            st.experimental_rerun()

def show_detalhes_hotel(hotel_id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT nome, cidade, endereco_rua, endereco_cidade, endereco_estado, endereco_cep, telefone, rating, preco FROM Hoteis WHERE Hotel_id = %s", (hotel_id,))
    hotel = cursor.fetchone()
    cursor.close()
    conn.close()

    if hotel:
        st.title(hotel[0])
        st.write(f"Local: {hotel[1]}, {hotel[2]}, {hotel[3]}, {hotel[4]}, CEP: {hotel[5]}")
        st.write(f"Telefone: {hotel[6]}")
        st.write(f"Rating: {hotel[7]}★")
        st.write(f"Preço da diária: R$ {hotel[8]:,.2f}")

        if st.button("Reservar este hotel"):
            st.session_state['current_page'] = "Reservar"
            st.session_state['current_hotel_id'] = hotel_id
            st.experimental_rerun()

def show_form_reserva(hotel_id):
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        st.session_state['target_page'] = 'Reservar'
        st.session_state['current_hotel_id'] = hotel_id
        st.session_state['current_page'] = 'Login'
        st.experimental_rerun()
        return

    st.title("Formulário de Reserva")
    nome_completo = st.text_input("Nome Completo")
    cpf = st.text_input("CPF")
    metodo_pagamento = st.selectbox("Método de Pagamento", ["Cartão de Crédito"])
    data_entrada = st.date_input("Data de Entrada", min_value=date.today())
    data_saida = st.date_input("Data de Saída", min_value=date.today())

    if data_entrada >= data_saida:
        st.error("A data de saída deve ser após a data de entrada")
        return

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT preco FROM Hoteis WHERE Hotel_id = %s", (hotel_id,))
    preco_diaria = cursor.fetchone()[0]
    cursor.close()
    conn.close()

    num_dias = (data_saida - data_entrada).days
    valor_reserva = num_dias * preco_diaria

    st.write(f"Valor total da reserva: R$ {valor_reserva:.2f}")

    if st.button("Confirmar Reserva"):
        conn = conectar()
        if conn is not None:
            try:
                cursor = conn.cursor()
                query = """
                INSERT INTO Reserva (Cliente_id, Hotel_id, Nome_completo, CPF, Metodo_pagamento, Data_entrada, Data_saida, Valor_reserva, Timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """
                cursor.execute(query, (st.session_state['user_id'], hotel_id, nome_completo, cpf, metodo_pagamento, data_entrada, data_saida, valor_reserva))
                reserva_id = cursor.lastrowid
                conn.commit()
                st.session_state['current_reserva_id'] = reserva_id
                st.session_state['current_page'] = "Pagamento"
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Erro ao inserir dados no banco de dados: {e}")
            finally:
                cursor.close()
                conn.close()

def process_payment(reserva_id, valor):
    conn = conectar()
    cursor = conn.cursor()
    try:
        payment_success = True

        if payment_success:
            cursor.execute("UPDATE Pagamento SET aprovado = TRUE WHERE reserva_id = %s", (reserva_id,))
            conn.commit()

            cursor.execute("SELECT email FROM Cliente WHERE cliente_id = (SELECT cliente_id FROM Reserva WHERE reserva_id = %s)", (reserva_id,))
            email = cursor.fetchone()[0]
            email_subject = "Confirmação de Pagamento - RoomEz"
            email_body = f"Olá,\n\nSeu pagamento de R$ {valor:.2f} foi processado com sucesso.\n\nDetalhes do pagamento:\nValor: R$ {valor:.2f}\n\nObrigado por usar o RoomEz!"
            send_email(email_subject, email_body, email)

            st.success("Pagamento realizado com sucesso!")
        else:
            st.error("Pagamento falhou. Por favor, tente novamente.")
    except Exception as e:
        st.error(f"Erro ao processar o pagamento: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def show_payment_page():
    if 'current_reserva_id' not in st.session_state:
        st.error("Nenhuma reserva encontrada.")
        st.session_state['current_page'] = "Home"
        st.experimental_rerun()
        return

    reserva_id = st.session_state['current_reserva_id']

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT Metodo_pagamento, Valor_reserva FROM Reserva WHERE Reserva_id = %s AND aceita = TRUE", (reserva_id,))
    reserva = cursor.fetchone()
    if reserva:
        metodo_pagamento = reserva[0]
        valor_reserva = reserva[1]
        cursor.close()
        conn.close()

        st.title("Pagamento")
        st.write(f"Valor total: R$ {valor_reserva:.2f}")

        if metodo_pagamento == "Cartão de Crédito":
            cartao_numero = st.text_input("Número do Cartão")
            
            col1, col2 = st.columns(2)
            with col1:
                cartao_mes = st.text_input("Validade Mês (MM)", max_chars=2)
            with col2:
                cartao_ano = st.text_input("Validade Ano (AA)", max_chars=2)
            
            cartao_cvc = st.text_input("CVC")
            if st.button("Pagar"):
                process_payment(reserva_id, valor_reserva)
    else:
        st.write("Pagamento não disponível. Certifique-se de que sua reserva foi aprovada.")
        cursor.close()
        conn.close()

def show_pagina_login():
    st.subheader("Login")
    email = st.text_input("Nome de usuário", key="login_email")
    senha = st.text_input("Senha", type="password", key="login_senha")

    login_col, signup_col = st.columns(2)
    with login_col:
        if st.button("Login"):
            authenticated, user_type, user_id = authenticate(email, senha)
            if authenticated:
                st.session_state['logged_in'] = True
                st.session_state['user_type'] = user_type
                st.session_state['user_id'] = user_id
                
                if 'target_page' in st.session_state:
                    target_page = st.session_state['target_page']
                    del st.session_state['target_page']
                    st.session_state['current_page'] = target_page
                else:
                    st.session_state['current_page'] = 'Painel do Proprietário' if user_type == 'proprietário' else 'Home'
                st.experimental_rerun()
            else:
                st.error("Usuário ou senha incorretos")

    with signup_col:
        if st.button("Cadastre-se"):
            st.session_state['current_page'] = "Cadastro"
            st.experimental_rerun()

def authenticate(email, senha):
    conn = conectar()
    if conn is not None:
        cursor = conn.cursor(buffered=True)
        try:
            cursor.execute("SELECT senha, 'cliente' as tipo_usuario, cliente_id FROM Cliente WHERE email = %s UNION SELECT senha, 'proprietário' as tipo_usuario, proprietario_id FROM Proprietario WHERE email = %s", (email, email))
            user_info = cursor.fetchone()
            if user_info and bcrypt.checkpw(senha.encode('utf-8'), user_info[0].encode('utf-8')):
                return True, user_info[1], user_info[2]  # Retorna True, tipo de usuário e ID
            return False, None, None
        except Exception as e:
            st.error(f"Erro ao verificar usuário: {e}")
            return False, None, None
        finally:
            cursor.close()
            conn.close()
    else:
        st.error("Não foi possível conectar ao banco de dados.")
        return False, None, None

def get_user_id(email):
    conn = conectar()
    if conn is not None:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT Cliente_id FROM Cliente WHERE email = %s", (email,))
            user_id = cursor.fetchone()
            return user_id[0] if user_id else None
        finally:
            cursor.close()
            conn.close()

def show_reservas():
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        st.warning("Você precisa estar logado para ver suas reservas.")
        show_pagina_login()
        return

    st.title("Suas Reservas")
    conn = conectar()
    if conn is not None:
        cursor = conn.cursor()
        query = "SELECT * FROM Reserva WHERE Cliente_id = %s"
        cursor.execute(query, (st.session_state['user_id'],))
        reservas = cursor.fetchall()
        if reservas:
            for reserva in reservas:
                st.write(f"Reserva no hotel {reserva[2]}, de {reserva[4]} até {reserva[5]}, valor: R$ {reserva[8]:,.2f}")
        else:
            st.write("Você não tem reservas.")
        cursor.close()
        conn.close()

def show_cadastro():
    st.title("Cadastro de Usuário")
    tipo_usuario = st.radio("Você é:", ["Cliente", "Proprietário"])
    nome = st.text_input("Nome Completo")
    email = st.text_input("Email")
    senha = st.text_input("Senha", type="password")
    confirmar_senha = st.text_input("Confirmar Senha", type="password")
    sexo = st.selectbox("Sexo", ["Masculino", "Feminino", "Outro"])

    if st.button("Registrar"):
        if senha == confirmar_senha:
            senha_hashed = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
            conn = conectar()
            if conn is not None:
                try:
                    cursor = conn.cursor()
                    if tipo_usuario == "Cliente":
                        query = """
                        INSERT INTO Cliente (Nome, Email, Senha, Sexo, tipo_usuario)
                        VALUES (%s, %s, %s, %s, %s)
                        """
                        cursor.execute(query, (nome, email, senha_hashed, sexo, 'cliente'))
                        email_subject = "Bem-vindo ao RoomEz!"
                        email_body = f"Olá {nome},\n\nObrigado por se cadastrar no RoomEz! Estamos felizes em tê-lo conosco.\n\nAtenciosamente,\nEquipe RoomEz"
                        send_email(email_subject, email_body, email)
                    elif tipo_usuario == "Proprietário":
                        query = """
                        INSERT INTO Proprietario (Nome, Email, Senha, tipo_usuario)
                        VALUES (%s, %s, %s, %s)
                        """
                        cursor.execute(query, (nome, email, senha_hashed, 'proprietario'))
                        email_subject = "Bem-vindo ao RoomEz!"
                        email_body = f"Olá {nome},\n\nObrigado por confiar no RoomEz para lidar com as reservas de seus hoteis! Estamos felizes em tê-lo conosco.\n\nAtenciosamente,\nEquipe RoomEz"
                        send_email(email_subject, email_body, email)
                    conn.commit()

                    st.success("Usuário registrado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao inserir dados no banco de dados: {e}")
                finally:
                    cursor.close()
                    conn.close()
        else:
            st.error("As senhas não coincidem.")

def show_consultas_proprietario():
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        st.error("Você precisa estar logado para acessar esta página.")
        return
    
    if 'user_type' not in st.session_state or st.session_state['user_type'] != 'proprietário':
        st.error("Acesso restrito a proprietários.")
        return

    st.title("Painel do Proprietário")

    opcao = st.selectbox(
        "Escolha a informação que deseja visualizar:",
        ("Hotéis", "Reservas", "Serviços", "Eventos", "Comentários", "Pagamentos")
    )

    conn = conectar()
    cursor = conn.cursor()

    if opcao == "Hotéis":
        cursor.execute("SELECT * FROM viewHoteisProprietario WHERE proprietario_id = %s", (st.session_state['user_id'],))
        data = cursor.fetchall()
        columns = ['Proprietário', 'Hotel ID', 'Nome', 'Cidade', 'Preço', 'Rating', 'Rua', 'Cidade', 'Estado', 'CEP', 'Telefone']
    elif opcao == "Reservas":
        cursor.execute("SELECT * FROM viewReservasPorHotel WHERE proprietario_id = %s", (st.session_state['user_id'],))
        data = cursor.fetchall()
        columns = ['Hotel', 'Reserva ID', 'Cliente', 'CPF', 'Método Pagamento', 'Data Entrada', 'Data Saída', 'Valor Reserva', 'Estado']
    elif opcao == "Serviços":
        cursor.execute("SELECT * FROM viewServicosPorHotel WHERE proprietario_id = %s", (st.session_state['user_id'],))
        data = cursor.fetchall()
        columns = ['Proprietário', 'Hotel', 'Serviço', 'Descrição', 'Preço']
    elif opcao == "Eventos":
        cursor.execute("SELECT * FROM viewEventosPorHotel WHERE proprietario_id = %s", (st.session_state['user_id'],))
        data = cursor.fetchall()
        columns = ['Proprietário', 'Hotel', 'Evento', 'Descrição', 'Data Início', 'Data Fim', 'Preço Ingresso']
    elif opcao == "Comentários":
        cursor.execute("SELECT * FROM viewComentariosPorHotel WHERE proprietario_id = %s", (st.session_state['user_id'],))
        data = cursor.fetchall()
        columns = ['Proprietário', 'Hotel', 'Comentário', 'Data', 'Rating']
    elif opcao == "Pagamentos":
        cursor.execute("SELECT * FROM viewPagamentosPorReserva WHERE proprietario_id = %s", (st.session_state['user_id'],))
        data = cursor.fetchall()
        columns = ['Hotel', 'Cliente', 'Reserva ID', 'Pagamento ID', 'Tipo', 'Valor', 'Aprovado']

    if data:
        st.table([columns] + list(data))
    else:
        st.write(f"Não há {opcao.lower()} cadastrados sob sua propriedade.")

    cursor.close()
    conn.close()

def show_pending_reservations():
    if 'logged_in' not in st.session_state or not st.session_state['logged_in'] or st.session_state['user_type'] != 'proprietário':
        st.error("Você precisa estar logado como proprietário para acessar esta página.")
        return

    st.title("Gerenciar Reservas Pendentes")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT r.reserva_id, h.nome, r.nome_completo, r.data_entrada, r.data_saida, r.valor_reserva
    FROM Reserva r
    JOIN Hoteis h ON r.hotel_id = h.hotel_id
    WHERE h.proprietario_id = %s AND r.aceita = FALSE
    """, (st.session_state['user_id'],))
    
    reservas = cursor.fetchall()
    if reservas:
        for reserva in reservas:
            with st.expander(f"Reserva {reserva[0]} - {reserva[1]}"):
                st.write(f"Cliente: {reserva[2]}")
                st.write(f"Data de Entrada: {reserva[3]}")
                st.write(f"Data de Saída: {reserva[4]}")
                st.write(f"Valor da Reserva: R$ {reserva[5]:,.2f}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Aceitar", key=f"aceitar_{reserva[0]}"):
                        update_reservation_status(reserva[0], True)
                with col2:
                    if st.button("Rejeitar", key=f"rejeitar_{reserva[0]}"):
                        update_reservation_status(reserva[0], False)
    else:
        st.write("Não há reservas pendentes.")
    
    cursor.close()
    conn.close()

def update_reservation_status(reserva_id, aceita):
    conn = conectar()
    cursor = conn.cursor()
    try:
        if aceita:
            cursor.execute("UPDATE Reserva SET aceita = TRUE WHERE reserva_id = %s", (reserva_id,))
            conn.commit()

            cursor.execute("SELECT email, nome_completo FROM Cliente WHERE cliente_id = (SELECT cliente_id FROM Reserva WHERE reserva_id = %s)", (reserva_id,))
            cliente_info = cursor.fetchone()
            email = cliente_info[0]
            nome_cliente = cliente_info[1]

            email_subject = "Reserva Aprovada!"
            email_body = f"Olá {nome_cliente},\n\nParabéns, sua reserva foi aprovada! Efetue o pagamento na página de pagamento."
            send_email(email_subject, email_body, email)

            cursor.execute("SELECT valor_reserva FROM Reserva WHERE reserva_id = %s", (reserva_id,))
            valor_reserva = cursor.fetchone()[0]
            cursor.execute("INSERT INTO Pagamento (reserva_id, tipo, valor, aprovado) VALUES (%s, 'Pendente', %s, FALSE)", (reserva_id, valor_reserva))
            conn.commit()

        else:
            cursor.execute("DELETE FROM Reserva WHERE reserva_id = %s", (reserva_id,))
            conn.commit()
        
        st.success("Reserva atualizada com sucesso!")
        st.experimental_rerun()
    except Exception as e:
        st.error(f"Erro ao atualizar reserva: {e}")
    finally:
        cursor.close()
        conn.close()

def show_comentarios(hotel_id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT comentario, data, rating FROM Comentarios WHERE hotel_id = %s", (hotel_id,))
    comentarios = cursor.fetchall()
    if comentarios:
        for comentario in comentarios:
            st.write(f"Data: {comentario[1]}, Rating: {comentario[2]} estrelas")
            st.text(comentario[0])
    else:
        st.write("Ainda não há comentários para este hotel.")
    cursor.close()
    conn.close()

def add_comentario(hotel_id, cliente_id, comentario, rating):
    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Comentarios (hotel_id, cliente_id, comentario, data, rating) VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s)", (hotel_id, cliente_id, comentario, rating))
        conn.commit()
        st.success("Comentário adicionado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao adicionar comentário: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def add_servico():
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        st.error("Você precisa estar logado para acessar esta página.")
        return
    
    if 'user_type' in st.session_state and st.session_state['user_type'] == 'proprietário':
        st.title("Adicionar Novo Serviço")
        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("SELECT hotel_id, nome FROM Hoteis WHERE proprietario_id = %s", (st.session_state['user_id'],))
        hoteis = cursor.fetchall()
        hotel_options = {hotel[1]: hotel[0] for hotel in hoteis}
        selected_hotel = st.selectbox("Selecione o Hotel", list(hotel_options.keys()))

        nome_servico = st.text_input("Nome do Serviço")
        descricao = st.text_area("Descrição do Serviço")
        preco = st.number_input("Preço do Serviço", min_value=0.0, format="%.2f")

        if st.button("Adicionar Serviço"):
            try:
                cursor.execute("""
                    INSERT INTO Servicos (hotel_id, nome_servico, descricao, preco)
                    VALUES (%s, %s, %s, %s)
                """, (hotel_options[selected_hotel], nome_servico, descricao, preco))
                conn.commit()
                st.success("Serviço adicionado com sucesso!")
            except Exception as e:
                st.error(f"Erro ao adicionar serviço: {e}")
                conn.rollback()
            finally:
                cursor.close()
                conn.close()
    else:
        st.error("Acesso restrito a proprietários.")

def add_evento():
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        st.error("Você precisa estar logado para acessar esta página.")
        return
    
    if 'user_type' in st.session_state and st.session_state['user_type'] == 'proprietário':
        st.title("Adicionar Novo Evento")
        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("SELECT hotel_id, nome FROM Hoteis WHERE proprietario_id = %s", (st.session_state['user_id'],))
        hoteis = cursor.fetchall()
        hotel_options = {hotel[1]: hotel[0] for hotel in hoteis}
        selected_hotel = st.selectbox("Selecione o Hotel", list(hotel_options.keys()))

        nome_evento = st.text_input("Nome do Evento")
        descricao = st.text_area("Descrição do Evento")
        data_inicio = st.date_input("Data de Início", min_value=date.today())
        data_fim = st.date_input("Data de Fim", min_value=data_inicio)
        preco_ingresso = st.number_input("Preço do Ingresso", min_value=0.0, format="%.2f")
        capacidade = st.number_input("Capacidade", min_value=1, step=1)

        if st.button("Adicionar Evento"):
            try:
                cursor.execute("""
                    INSERT INTO Eventos (hotel_id, nome_evento, descricao, data_inicio, data_fim, preco_ingresso, capacidade)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (hotel_options[selected_hotel], nome_evento, descricao, data_inicio, data_fim, preco_ingresso, capacidade))
                conn.commit()
                st.success("Evento adicionado com sucesso!")
            except Exception as e:
                st.error(f"Erro ao adicionar evento: {e}")
                conn.rollback()
            finally:
                cursor.close()
                conn.close()
    else:
        st.error("Acesso restrito a proprietários.")

def add_hotel():
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        st.error("Você precisa estar logado para acessar esta página.")
        return

    if 'user_type' in st.session_state and st.session_state['user_type'] == 'proprietário':
        st.title("Adicionar Novo Hotel")

        nome = st.text_input("Nome do Hotel")
        cidade = st.text_input("Cidade")
        preco = st.number_input("Preço por Noite", min_value=0.0, format="%.2f")
        rating = st.number_input("Rating", min_value=0.0, max_value=5.0, format="%.1f")
        rua = st.text_input("Endereço - Rua")
        estado = st.text_input("Endereço - Estado")
        cep = st.text_input("Endereço - CEP")
        telefone = st.text_input("Telefone")

        if st.button("Adicionar Hotel"):
            if nome and cidade and preco and rua and estado and cep and telefone:
                conn = conectar()
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        INSERT INTO Hoteis (nome, cidade, preco, rating, endereco_rua, endereco_estado, endereco_cep, telefone, proprietario_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (nome, cidade, preco, rating, rua, estado, cep, telefone, st.session_state['user_id']))
                    conn.commit()
                    st.success("Hotel adicionado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao adicionar hotel: {e}")
                    conn.rollback()
                finally:
                    cursor.close()
                    conn.close()
            else:
                st.error("Todos os campos devem ser preenchidos.")
    else:
        st.error("Acesso restrito a proprietários.")

def show_hotels_to_edit_or_delete():
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        st.error("Você precisa estar logado para acessar esta página.")
        return

    if 'user_type' in st.session_state and st.session_state['user_type'] == 'proprietário':
        st.title("Gerenciar Hotéis")

        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT hotel_id, nome FROM Hoteis WHERE proprietario_id = %s", (st.session_state['user_id'],))
        hotels = cursor.fetchall()
        cursor.close()
        conn.close()

        if not hotels:
            st.write("Você não tem hotéis cadastrados.")
            return

        hotel_options = {hotel[1]: hotel[0] for hotel in hotels}
        selected_hotel_name = st.selectbox("Selecione o Hotel", list(hotel_options.keys()))
        selected_hotel_id = hotel_options[selected_hotel_name]

        if st.button("Excluir Hotel"):
            delete_hotel(selected_hotel_id)

        st.write("Ou você pode editar os detalhes do hotel abaixo:")
        nome = st.text_input("Nome do Hotel", value=selected_hotel_name)
        cidade = st.text_input("Cidade")
        preco = st.number_input("Preço por Noite", min_value=0.0, format="%.2f")
        rating = st.number_input("Rating", min_value=0.0, max_value=5.0, format="%.1f")
        rua = st.text_input("Endereço - Rua")
        estado = st.text_input("Endereço - Estado")
        cep = st.text_input("Endereço - CEP")
        telefone = st.text_input("Telefone")
        foto = st.text_input("URL da Foto")

        if st.button("Atualizar Hotel"):
            update_hotel(selected_hotel_id, nome, cidade, preco, rating, rua, estado, cep, telefone, foto)
    else:
        st.error("Acesso restrito a proprietários.")

def delete_hotel(hotel_id):
    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Hoteis WHERE hotel_id = %s", (hotel_id,))
        conn.commit()
        st.success("Hotel excluído com sucesso!")
    except Exception as e:
        st.error(f"Erro ao excluir hotel: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def update_hotel(hotel_id, nome, cidade, preco, rating, rua, estado, cep, telefone, foto):
    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE Hoteis
            SET nome = %s, cidade = %s, preco = %s, rating = %s, endereco_rua = %s, endereco_estado = %s, endereco_cep = %s, telefone = %s, foto = %s
            WHERE hotel_id = %s
        """, (nome, cidade, preco, rating, rua, estado, cep, telefone, foto, hotel_id))
        conn.commit()
        st.success("Hotel atualizado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao atualizar hotel: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def main():
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = "Home"
    
    st.sidebar.title("Menu")
    app_mode = st.sidebar.selectbox("Escolha uma opção",
                                    ["Home", "Cadastro", "Reservas", "Login", "Painel do Proprietário", "Gerenciar Reservas Pendentes", "Hotel", "Reservar", "Pagamento", "Adicionar Serviço", "Adicionar Comentario", "Adicionar Evento", "Adicionar Hotel", "Gerenciar Hotel"],
                                    index=["Home", "Cadastro", "Reservas", "Login", "Painel do Proprietário", "Gerenciar Reservas Pendentes", "Hotel", "Reservar", "Pagamento", "Adicionar Serviço", "Adicionar Comentario", "Adicionar Evento", "Adicionar Hotel", "Gerenciar Hotel"].index(st.session_state.get('current_page', 'Home')))

    if app_mode == "Home":
        st.session_state['current_page'] = "Home"
        show_home()
    elif app_mode == "Cadastro":
        st.session_state['current_page'] = "Cadastro"
        show_cadastro()
    elif app_mode == "Reservas":
        st.session_state['current_page'] = "Reservas"
        show_reservas()
    elif app_mode == "Login":
        st.session_state['current_page'] = "Login"
        show_pagina_login()
    elif app_mode == "Hotel":
        if 'current_hotel_id' in st.session_state:
            show_detalhes_hotel(st.session_state['current_hotel_id'])
    elif app_mode == "Reservar":
        if 'current_hotel_id' in st.session_state:
            show_form_reserva(st.session_state['current_hotel_id'])
    elif app_mode == "Pagamento":
        show_payment_page()
    elif app_mode == "Painel do Proprietário":
        st.session_state['current_page'] = "Painel do Proprietário"
        show_consultas_proprietario()
    elif app_mode == "Gerenciar Reservas Pendentes":
        st.session_state['current_page'] = "Gerenciar Reservas Pendentes"
        show_pending_reservations()
    elif app_mode == "Adicionar Serviço":
        st.session_state['current_page'] = "Adicionar Serviço"
        add_servico()
    elif app_mode == "Adicionar Comentario":
        st.session_state['current_page'] = "Adicionar Comentario"
        add_comentario()
    elif app_mode == "Adicionar Evento":
        st.session_state['current_page'] = "Adicionar Evento"
        add_evento()
    elif app_mode == "Adicionar Hotel":
        st.session_state['current_page'] = "Adicionar Hotel"
        add_hotel()
    elif app_mode == "Gerenciar Hotel":
        st.session_state['current_page'] = "Gerenciar Hotel"
        show_hotels_to_edit_or_delete()

if __name__ == "__main__":
    main()

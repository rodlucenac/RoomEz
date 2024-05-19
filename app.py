import streamlit as st
from banco import conectar
import bcrypt
from datetime import date
import threading
import time

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

def show_hotel_details(hotel_id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT nome, cidade, endereco_rua, endereco_cidade, endereco_estado, endereco_cep, telefone, rating, preco, foto FROM Hoteis WHERE Hotel_id = %s", (hotel_id,))
    hotel = cursor.fetchone()
    cursor.close()
    conn.close()

    if hotel:
        st.title(hotel[0])
        st.image(hotel[9], use_column_width=True)
        st.write(f"Local: {hotel[1]}, {hotel[2]}, {hotel[3]}, {hotel[4]}, CEP: {hotel[5]}")
        st.write(f"Telefone: {hotel[6]}")
        st.write(f"Rating: {hotel[7]}★")
        st.write(f"Preço da diária: R$ {hotel[8]:,.2f}")

        if st.button("Reservar este hotel"):
            st.session_state['current_page'] = "Reservar"
            st.session_state['current_hotel_id'] = hotel_id
            st.experimental_rerun()

def show_reservation_form(hotel_id):
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        st.session_state['target_page'] = 'Reservar'
        st.session_state['current_hotel_id'] = hotel_id
        st.session_state['current_page'] = 'Login'
        st.experimental_rerun()
        return

    st.title("Formulário de Reserva")
    nome_completo = st.text_input("Nome Completo")
    cpf = st.text_input("CPF")
    metodo_pagamento = st.selectbox("Método de Pagamento", ["Cartão de Crédito", "Boleto", "Pix"])
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

def show_payment_page():
    if 'current_reserva_id' not in st.session_state:
        st.error("Nenhuma reserva encontrada.")
        st.session_state['current_page'] = "Pagamento"
        st.experimental_rerun()
        return

    reserva_id = st.session_state['current_reserva_id']

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT Metodo_pagamento, Valor_reserva FROM Reserva WHERE Reserva_id = %s", (reserva_id,))
    reserva = cursor.fetchone()
    metodo_pagamento = reserva[0]
    valor_reserva = reserva[1]
    cursor.close()
    conn.close()

    st.title("Pagamento")
    st.write(f"Valor total: R$ {valor_reserva:.2f}")

    if metodo_pagamento == "Cartão de Crédito":
        cartao_numero = st.text_input("Número do Cartão")
        cartao_validade = st.text_input("Validade (MM/AA)")
        cartao_cvc = st.text_input("CVC")
        if st.button("Pagar"):
            # Simular a inserção do pagamento no banco de dados
            conn = conectar()
            cursor = conn.cursor()
            try:
                query = "INSERT INTO Pagamento (Reserva_id, Tipo, Aprovado, Valor) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (reserva_id, "Cartão de Crédito", True, valor_reserva))
                conn.commit()
                st.success("Pagamento realizado com sucesso!")
                st.session_state['current_page'] = "Home"
                del st.session_state['current_reserva_id']
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Erro ao registrar pagamento: {e}")
            finally:
                cursor.close()
                conn.close()
    elif metodo_pagamento == "Boleto":
        # Simular a geração de boleto
        conn = conectar()
        cursor = conn.cursor()
        try:
            query = "INSERT INTO Pagamento (Reserva_id, Tipo, Aprovado, Valor) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (reserva_id, "Boleto", False, valor_reserva))
            conn.commit()
            st.success("Boleto gerado com sucesso! Pague no seu banco ou app de preferência.")
            st.session_state['current_page'] = "Home"
            del st.session_state['current_reserva_id']
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Erro ao registrar pagamento: {e}")
        finally:
            cursor.close()
            conn.close()
    elif metodo_pagamento == "Pix":
        # Simular a geração de chave PIX
        conn = conectar()
        cursor = conn.cursor()
        try:
            query = "INSERT INTO Pagamento (Reserva_id, Tipo, Aprovado, Valor) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (reserva_id, "Pix", False, valor_reserva))
            conn.commit()
            st.success("Use a chave PIX acima para realizar o pagamento.")
            st.session_state['current_page'] = "Home"
            del st.session_state['current_reserva_id']
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Erro ao registrar pagamento: {e}")
        finally:
            cursor.close()
            conn.close()

def show_login_page():
    st.subheader("Login")
    email = st.text_input("Nome de usuário", key="login_email")
    senha = st.text_input("Senha", type="password", key="login_senha")

    login_col, signup_col = st.columns(2)
    with login_col:
        if st.button("Login"):
            if authenticate(email, senha):
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = get_user_id(email)
                if 'target_page' in st.session_state:
                    target_page = st.session_state['target_page']
                    del st.session_state['target_page']
                    st.session_state['current_page'] = target_page
                else:
                    st.session_state['current_page'] = 'Home'
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
            cursor.execute("SELECT senha FROM Cliente WHERE email = %s", (email,))
            senha_hashed = cursor.fetchone()
            if senha_hashed and bcrypt.checkpw(senha.encode('utf-8'), senha_hashed[0].encode('utf-8')):
                return True
            else:
                return False
        except Exception as e:
            st.error(f"Erro ao verificar usuário: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

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
        show_login_page()
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
    st.title("Cadastro de Cliente")
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
                    query = """
                    INSERT INTO Cliente (Nome, Email, Senha, Sexo)
                    VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(query, (nome, email, senha_hashed, sexo))
                    conn.commit()
                    st.success("Cliente registrado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao inserir dados no banco de dados: {e}")
                finally:
                    cursor.close()
                    conn.close()
        else:
            st.error("As senhas não coincidem.")

def cancelar_reservas_nao_pagas():
    while True:
        conn = conectar()
        if conn is not None:
            try:
                cursor = conn.cursor()
                query = """
                DELETE FROM Reserva
                WHERE TIMESTAMPDIFF(MINUTE, Timestamp, NOW()) > 30
                AND Reserva_id NOT IN (
                    SELECT Reserva_id FROM Pagamento
                )
                """
                cursor.execute(query)
                conn.commit()
                cursor.close()
            except Exception as e:
                print(f"Erro ao cancelar reservas: {e}")
            finally:
                conn.close()
        time.sleep(1800)

def main():
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = "Home"

    if 'reservas_thread' not in st.session_state:
        st.session_state['reservas_thread'] = threading.Thread(target=cancelar_reservas_nao_pagas)
        st.session_state['reservas_thread'].daemon = True
        st.session_state['reservas_thread'].start()
    
    st.sidebar.title("Menu")
    app_mode = st.sidebar.selectbox("Escolha uma opção",
                                    ["Home", "Cadastro", "Reservas", "Login", "Hotel", "Reservar", "Pagamento"],
                                    index=["Home", "Cadastro", "Reservas", "Login", "Hotel", "Reservar", "Pagamento"].index(st.session_state.get('current_page', 'Home')))

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
        show_login_page()
    elif app_mode == "Hotel":
        if 'current_hotel_id' in st.session_state:
            show_hotel_details(st.session_state['current_hotel_id'])
    elif app_mode == "Reservar":
        if 'current_hotel_id' in st.session_state:
            show_reservation_form(st.session_state['current_hotel_id'])
    elif app_mode == "Pagamento":
        show_payment_page()

if __name__ == "__main__":
    main()

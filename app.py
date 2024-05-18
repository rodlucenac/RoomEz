import streamlit as st
from banco import conectar

def show_cadastro():
    st.title("Cadastro de Cliente")
    st.subheader("Cadastro de Cliente")
    nome = st.text_input("Nome Completo")
    email = st.text_input("Email")
    senha = st.text_input("Senha", type="password")
    confirmar_senha = st.text_input("Confirmar Senha", type="password")
    sexo = st.selectbox("Sexo", ["Masculino", "Feminino", "Outro"])

    if st.button("Registrar"):
        if senha == confirmar_senha:
            st.success("Cliente registrado com sucesso!")
        else:
            st.error("As senhas não coincidem.")

def show_reservas():
    st.title("Reservas")
    st.subheader("Fazer Reserva")
    nome_completo = st.text_input("Nome Completo")
    cpf = st.text_input("CPF")
    tipo_quarto = st.selectbox("Tipo de Quarto", ["Simples", "Duplo", "Suite"])
    metodo_pagamento = st.selectbox("Método de Pagamento", ["Cartão de Crédito", "Boleto", "Pix"])
    data_entrada = st.date_input("Data de Entrada")
    data_saida = st.date_input("Data de Saída")
    
    if st.button("Reservar"):
        st.success("Reserva realizada com sucesso!")

def show_home():
    st.title("Página Inicial - Escolha um Hotel")
    
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT cidade FROM Hoteis")
    cidades = cursor.fetchall()
    cidade_escolhida = st.selectbox("Escolha a cidade", [cidade[0] for cidade in cidades])

    ordenacao = st.selectbox("Ordenar por", ["Rating", "Menor Preço", "Maior Preço"])
    
    query = "SELECT nome, preco, rating FROM Hoteis WHERE cidade = %s"
    if ordenacao == "Rating":
        query += " ORDER BY rating DESC"
    elif ordenacao == "Menor Preço":
        query += " ORDER BY preco ASC"
    else:
        query += " ORDER BY preco DESC"
    
    cursor.execute(query, (cidade_escolhida,))
    hoteis = cursor.fetchall()
    
    for hotel in hoteis:
        st.subheader(f"{hotel[0]} - {hotel[2]}★")
        st.text(f"Preço por noite: R$ {hotel[1]:,.2f}")
        
    cursor.close()
    conn.close()
def show_login_page():
    st.subheader("Login")
    username = st.text_input("Nome de usuário", key="login_username")
    password = st.text_input("Senha", type="password", key="login_password")

    login_col, signup_col = st.columns(2)  # Divide a linha em duas colunas para os botões
    with login_col:
        if st.button("Login"):
            if authenticate(username, password):  # Suponha que você tem uma função para autenticar
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = get_user_id(username)  # Suponha que você tem uma função para pegar o ID do usuário
                st.experimental_rerun()
            else:
                st.error("Usuário ou senha incorretos")

    with signup_col:
        if st.button("Cadastre-se"):
            st.session_state['current_page'] = show_cadastro()

def authenticate(email, senha):
    # Aqui você implementaria a lógica de autenticação
    return True  # Simulação de autenticação bem-sucedida

def get_user_id(email):
    # Simulação de obtenção do ID de usuário
    return 1

def show_reservas():
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        st.warning("Você precisa estar logado para ver suas reservas.")
        show_login_page()
        return

    st.title("Suas Reservas")
    conn = conectar()
    if conn is not None:
        cursor = conn.cursor()
        query = "SELECT * FROM Reservas WHERE cliente_id = %s"
        cursor.execute(query, (st.session_state['user_id'],))
        reservas = cursor.fetchall()
        if reservas:
            for reserva in reservas:
                st.write(f"Reserva no {reserva[2]}, de {reserva[4]} até {reserva[5]}")
        else:
            st.write("Você não tem reservas.")
        cursor.close()
        conn.close()
def main():
    st.sidebar.title("Menu")
    app_mode = st.sidebar.selectbox("Escolha uma opção",
                                    ["Home", "Cadastro", "Reservas"])

    if app_mode == "Home":
        show_home()
    elif app_mode == "Cadastro":
        show_cadastro()
    elif app_mode == "Reservas":
        show_reservas()

if __name__ == "__main__":
    main()

def test_new_loan_form_shows_only_admin_and_operator_as_approvers(
    client,
    login_user,
    create_system_user,
):
    """
    A tela de novo empréstimo deve listar como aprovadores apenas usuários ativos
    ADMIN ou OPERADOR.
    """

    login_user(
        email="admin.form@teste.com",
        role="ADMIN",
    )

    create_system_user(
        nome="Aprovador Admin",
        email="aprovador.admin@teste.com",
        role="ADMIN",
        active=True,
    )

    create_system_user(
        nome="Aprovador Operador",
        email="aprovador.operador@teste.com",
        role="OPERADOR",
        active=True,
    )

    create_system_user(
        nome="Usuário Consulta",
        email="consulta.nao.aprova@teste.com",
        role="CONSULTA",
        active=True,
    )

    create_system_user(
        nome="Operador Inativo",
        email="operador.inativo@teste.com",
        role="OPERADOR",
        active=False,
    )

    response = client.get(
        "/emprestimos/novo",
        follow_redirects=True,
    )

    assert response.status_code == 200

    assert "aprovador.admin@teste.com".encode("utf-8") in response.data
    assert "aprovador.operador@teste.com".encode("utf-8") in response.data

    assert "consulta.nao.aprova@teste.com".encode("utf-8") not in response.data
    assert "operador.inativo@teste.com".encode("utf-8") not in response.data
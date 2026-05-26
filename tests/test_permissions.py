from models.system_user import SystemUser


def test_admin_can_access_users_page(client, login_user):
    """
    ADMIN pode acessar a tela de usuários.
    """

    login_user(
        email="admin@teste.com",
        role="ADMIN",
    )

    response = client.get(
        "/auth/usuarios",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Usuários do sistema".encode("utf-8") in response.data


def test_operator_cannot_access_users_page(client, login_user):
    """
    OPERADOR não pode acessar gerenciamento de usuários.
    """

    login_user(
        email="operador@teste.com",
        role="OPERADOR",
    )

    response = client.get(
        "/auth/usuarios",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Acesso restrito ao administrador".encode("utf-8") in response.data


def test_consulta_cannot_access_users_page(client, login_user):
    """
    CONSULTA não pode acessar gerenciamento de usuários.
    """

    login_user(
        email="consulta@teste.com",
        role="CONSULTA",
    )

    response = client.get(
        "/auth/usuarios",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Acesso restrito ao administrador".encode("utf-8") in response.data


def test_admin_can_access_maintenance_page(client, login_user):
    """
    ADMIN pode acessar manutenção.
    """

    login_user(
        email="admin2@teste.com",
        role="ADMIN",
    )

    response = client.get(
        "/manutencao/",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Manutenção do sistema".encode("utf-8") in response.data


def test_operator_cannot_access_maintenance_page(client, login_user):
    """
    OPERADOR não pode acessar manutenção.
    """

    login_user(
        email="operador2@teste.com",
        role="OPERADOR",
    )

    response = client.get(
        "/manutencao/",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Acesso restrito ao administrador".encode("utf-8") in response.data


def test_consulta_can_access_items_list(client, login_user):
    """
    CONSULTA pode visualizar itens.
    """

    login_user(
        email="consulta2@teste.com",
        role="CONSULTA",
    )

    response = client.get(
        "/itens/",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Equipamentos e materiais cadastrados".encode("utf-8") in response.data


def test_consulta_cannot_create_user(client, app, login_user):
    """
    CONSULTA não pode executar POST para criar usuário.
    """

    login_user(
        email="consulta3@teste.com",
        role="CONSULTA",
    )

    response = client.post(
        "/auth/usuarios/novo",
        data={
            "nome": "Usuário Bloqueado",
            "email": "bloqueado@teste.com",
            "password": "123456",
            "role": "OPERADOR",
            "active": "on",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        user = SystemUser.query.filter_by(
            email="bloqueado@teste.com"
        ).first()

        assert user is None
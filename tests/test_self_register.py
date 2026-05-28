from database.database import db
from enums.user_role import UserRole
from models.system_user import SystemUser


def test_login_page_shows_self_register_link(
    client,
    create_system_user,
):
    create_system_user(
        nome="Admin Existente",
        email="admin.existente@teste.com",
        password="123456",
        role="ADMIN",
        active=True,
    )

    response = client.get(
        "/auth/login",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Criar cadastro de consulta".encode("utf-8") in response.data


def test_self_register_creates_consulta_user(
    client,
    app,
    create_system_user,
):
    create_system_user(
        nome="Admin Existente",
        email="admin.existente@teste.com",
        password="123456",
        role="ADMIN",
        active=True,
    )

    response = client.post(
        "/auth/cadastrar",
        data={
            "nome": "Usuário Consulta Novo",
            "matricula": "999999",
            "email": "consulta.novo@teste.com",
            "telefone": "31999999999",
            "gerencia": "GERÊNCIA TESTE",
            "regional": "REGIONAL TESTE",
            "equipe": "EQUIPE TESTE",
            "password": "Senha123",
            "confirm_password": "Senha123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Cadastro realizado com sucesso".encode("utf-8") in response.data

    with app.app_context():
        user = SystemUser.query.filter_by(
            email="consulta.novo@teste.com"
        ).first()

        assert user is not None
        assert user.role == UserRole.CONSULTA.value
        assert user.active is True
        assert user.matricula == "999999"
        assert user.gerencia == "GERÊNCIA TESTE"


def test_self_register_does_not_allow_first_user_to_bypass_admin_setup(
    client,
):
    response = client.get(
        "/auth/cadastrar",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/auth/primeiro-admin" in response.headers["Location"]
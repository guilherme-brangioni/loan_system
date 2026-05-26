from models.system_user import SystemUser
from database.database import db


def test_redirect_to_first_admin_when_no_users(client):
    """
    Se não existir usuário cadastrado, o sistema deve redirecionar
    para criação do primeiro administrador.
    """

    response = client.get("/", follow_redirects=False)

    assert response.status_code in [302, 308]
    assert "/auth/primeiro-admin" in response.location


def test_create_first_admin(client, app):
    """
    Testa criação do primeiro administrador.
    """

    response = client.post(
        "/auth/primeiro-admin",
        data={
            "nome": "Administrador",
            "email": "admin@teste.com",
            "password": "123456",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        user = SystemUser.query.filter_by(
            email="admin@teste.com"
        ).first()

        assert user is not None
        assert user.role == "ADMIN"
        assert user.active is True


def test_login_with_admin(client, app):
    """
    Testa login com usuário administrador existente.
    """

    with app.app_context():
        user = SystemUser()
        user.nome = "Administrador"
        user.email = "admin@teste.com"
        user.role = "ADMIN"
        user.active = True
        user.set_password("123456")

        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/auth/login",
        data={
            "email": "admin@teste.com",
            "password": "123456",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Dashboard".encode("utf-8") in response.data


def test_invalid_login(client, app):
    """
    Testa tentativa de login inválida.
    """

    with app.app_context():
        user = SystemUser()
        user.nome = "Administrador"
        user.email = "admin@teste.com"
        user.role = "ADMIN"
        user.active = True
        user.set_password("senha-correta")

        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/auth/login",
        data={
            "email": "admin@teste.com",
            "password": "senha-errada",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "E-mail ou senha inválidos".encode("utf-8") in response.data
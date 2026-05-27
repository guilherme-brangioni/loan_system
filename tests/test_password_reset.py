from database.database import db
from models.system_user import SystemUser


def test_forgot_password_marks_user_to_change_password(
    client,
    app,
    create_system_user,
):
    """
    Ao solicitar 'esqueci minha senha', o usuário ativo deve receber senha temporária
    e ficar obrigado a alterar a senha no próximo login.

    O envio de e-mail é mockado no conftest.py.
    """

    user_id = create_system_user(
        nome="Usuário Reset",
        email="reset@teste.com",
        password="SenhaAntiga123",
        role="OPERADOR",
        active=True,
    )

    response = client.post(
        "/auth/esqueci-senha",
        data={
            "email": "reset@teste.com",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "senha temporária".encode("utf-8") in response.data

    with app.app_context():
        user = db.session.get(SystemUser, user_id)

        assert user is not None
        assert user.must_change_password is True
        assert user.temporary_password_generated_at is not None


def test_forgot_password_with_unknown_email_does_not_fail(
    client,
):
    """
    E-mail inexistente não deve revelar se o usuário existe ou não.
    """

    response = client.post(
        "/auth/esqueci-senha",
        data={
            "email": "naoexiste@teste.com",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "senha temporária".encode("utf-8") in response.data


def test_login_with_temporary_password_redirects_to_force_change(
    client,
    app,
    create_system_user,
):
    """
    Usuário marcado com must_change_password deve ser redirecionado
    para troca obrigatória após login.
    """

    user_id = create_system_user(
        nome="Usuário Temporário",
        email="temporario@teste.com",
        password="SenhaTemp123",
        role="CONSULTA",
        active=True,
    )

    with app.app_context():
        user = db.session.get(SystemUser, user_id)

        assert user is not None

        user.must_change_password = True

        db.session.commit()

    response = client.post(
        "/auth/login",
        data={
            "email": "temporario@teste.com",
            "password": "SenhaTemp123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Crie uma nova senha".encode("utf-8") in response.data


def test_force_change_password_updates_password_and_releases_access(
    client,
    app,
    create_system_user,
):
    """
    Após trocar a senha obrigatória, must_change_password deve voltar para False.
    """

    user_id = create_system_user(
        nome="Usuário Troca Obrigatória",
        email="troca.obrigatoria@teste.com",
        password="SenhaTemp123",
        role="CONSULTA",
        active=True,
    )

    with app.app_context():
        user = db.session.get(SystemUser, user_id)

        assert user is not None

        user.must_change_password = True

        db.session.commit()

    login_response = client.post(
        "/auth/login",
        data={
            "email": "troca.obrigatoria@teste.com",
            "password": "SenhaTemp123",
        },
        follow_redirects=True,
    )

    assert login_response.status_code == 200
    assert "Crie uma nova senha".encode("utf-8") in login_response.data

    change_response = client.post(
        "/auth/alterar-senha-obrigatoria",
        data={
            "new_password": "NovaSenha123",
            "confirm_password": "NovaSenha123",
        },
        follow_redirects=True,
    )

    assert change_response.status_code == 200
    assert "Senha alterada com sucesso".encode("utf-8") in change_response.data

    with app.app_context():
        user = db.session.get(SystemUser, user_id)

        assert user is not None
        assert user.must_change_password is False
        assert user.password_changed_at is not None
        assert user.check_password("NovaSenha123") is True


def test_admin_can_reset_user_password(
    client,
    app,
    login_user,
    create_system_user,
):
    """
    ADMIN pode resetar senha de outro usuário.
    """

    login_user(
        email="admin.reset@teste.com",
        role="ADMIN",
    )

    user_id = create_system_user(
        nome="Usuário Reset Admin",
        email="reset.admin@teste.com",
        password="SenhaAntiga123",
        role="OPERADOR",
        active=True,
    )

    response = client.post(
        f"/auth/usuarios/{user_id}/resetar-senha",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Senha temporária enviada".encode("utf-8") in response.data

    with app.app_context():
        user = db.session.get(SystemUser, user_id)

        assert user is not None
        assert user.must_change_password is True
        assert user.temporary_password_generated_at is not None


def test_operator_cannot_reset_user_password(
    client,
    app,
    login_user,
    create_system_user,
):
    """
    OPERADOR não pode resetar senha de usuários.
    """

    login_user(
        email="operador.reset@teste.com",
        role="OPERADOR",
    )

    user_id = create_system_user(
        nome="Usuário Bloqueado Reset",
        email="bloqueado.reset@teste.com",
        password="SenhaAntiga123",
        role="CONSULTA",
        active=True,
    )

    response = client.post(
        f"/auth/usuarios/{user_id}/resetar-senha",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Acesso restrito ao administrador".encode("utf-8") in response.data

    with app.app_context():
        user = db.session.get(SystemUser, user_id)

        assert user is not None
        assert user.must_change_password is False
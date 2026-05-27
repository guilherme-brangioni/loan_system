def test_logged_user_can_access_my_profile(
    client,
    login_user,
):
    """
    Usuário logado pode acessar Meu Perfil.
    """

    login_user(
        email="perfil@teste.com",
        role="OPERADOR",
    )

    response = client.get(
        "/auth/meu-perfil",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Meu perfil".encode("utf-8") in response.data
    assert "perfil@teste.com".encode("utf-8") in response.data


def test_anonymous_user_cannot_access_my_profile(
    client,
    create_system_user,
):
    """
    Usuário não logado deve ser redirecionado para login
    quando já existe pelo menos um usuário cadastrado.
    """

    create_system_user(
        nome="Usuário Existente",
        email="existente@teste.com",
        password="123456",
        role="ADMIN",
        active=True,
    )

    response = client.get(
        "/auth/meu-perfil",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]
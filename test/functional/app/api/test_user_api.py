import pytest, json


@pytest.mark.parametrize("reset_user_id_accessor,status_code", [
    (lambda u: 100, 404),
    (lambda u: None, 400),
    (lambda u: u.id, 200),
])
def test_admin_reset_user_pin(
        test_client, complete_admin_auth_token, create_transfer_account_user, reset_user_id_accessor, status_code
):
    user_id = reset_user_id_accessor(create_transfer_account_user)
    response = test_client.post('/api/v1/user/reset_pin/',
                                headers=dict(Authorization=complete_admin_auth_token, Accept='application/json'),
                                data=json.dumps(dict(user_id=user_id)),
                                content_type='application/json', follow_redirects=True)
    assert response.status_code == status_code
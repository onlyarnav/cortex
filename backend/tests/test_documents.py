def test_upload_rejects_invalid_file_type(client, auth_token):
    response = client.post(
        "/documents/upload",
        files={"file": ("test.exe", b"fake content", "application/octet-stream")},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 400


def test_list_documents_requires_auth(client):
    response = client.get("/documents/")
    assert response.status_code == 401
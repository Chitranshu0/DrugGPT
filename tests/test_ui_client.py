from unittest.mock import Mock, patch

from src.ui.api_client import DrugGPTApiClient


@patch("src.ui.api_client.requests.request")
def test_ui_client_sends_chat_payload(mock_request):
    response = Mock()
    response.json.return_value = {"answer": "ok", "sources": []}
    response.raise_for_status = Mock()
    mock_request.return_value = response
    client = DrugGPTApiClient("http://api")
    result = client.send_message("conv-1", "Question")
    assert result["answer"] == "ok"
    assert mock_request.call_args.kwargs["json"] == {"message": "Question"}
    assert mock_request.call_args.args[0] == "POST"
    assert mock_request.call_args.args[1] == "http://api/conversations/conv-1/messages"


@patch("src.ui.api_client.requests.request")
def test_ui_client_rebuild_passes_timeout(mock_request):
    response = Mock()
    response.json.return_value = {"message": "Index rebuilt.", "documents_indexed": 2, "chunks_indexed": 10}
    response.raise_for_status = Mock()
    mock_request.return_value = response
    client = DrugGPTApiClient("http://api")
    result = client.rebuild()
    assert result["message"] == "Index rebuilt."
    assert mock_request.call_args.kwargs["timeout"] == 600

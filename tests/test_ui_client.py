from unittest.mock import Mock, patch

from druggpt.ui.api_client import DrugGPTApiClient


@patch("druggpt.ui.api_client.requests.post")
def test_ui_client_sends_chat_payload(post):
    response = Mock()
    response.json.return_value = {"answer": "ok", "sources": []}
    post.return_value = response
    result = DrugGPTApiClient("http://api").chat("Question", "thread-1")
    assert result["answer"] == "ok"
    assert post.call_args.kwargs["json"] == {"message": "Question", "thread_id": "thread-1"}

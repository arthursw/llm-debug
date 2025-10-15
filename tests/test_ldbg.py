import inspect
import builtins
import types

import ldbg.ldbg as ldbg


def test_extract_code_blocks_single_block():
    md = "Here is some text\n```python\nprint('hello')\n```\nmore text"
    blocks = ldbg.extract_code_blocks(md)
    assert blocks == ["print('hello')\n"]


def test_extract_code_blocks_multiple_blocks():
    md = "```\na=1\n```\ntext\n```py\nb=2\n```"
    blocks = ldbg.extract_code_blocks(md)
    assert blocks == ["a=1\n", "b=2\n"]


def test_execute_code_block_prints_output(capsys):
    # execute_code_block uses exec(..., {}) so it runs in an empty namespace.
    ldbg.execute_code_block("print('hi from code block')")
    captured = capsys.readouterr()
    assert "hi from code block" in captured.out


def test_execute_blocks_none_does_nothing(capsys):
    # Should not raise and should not print anything
    ldbg.execute_blocks(None)
    captured = capsys.readouterr()
    assert captured.out == ""


def test_execute_blocks_user_confirms_exec(monkeypatch, capsys):
    # Provide markdown with a single code block.
    md = "Some text\n```\nprint('ran')\n```\n"
    # Simulate user input 'y'
    monkeypatch.setattr(builtins, "input", lambda prompt="": "y")
    executed = {"called": False, "code": None}

    def fake_exec_block(code):
        executed["called"] = True
        executed["code"] = code

    monkeypatch.setattr(ldbg, "execute_code_block", fake_exec_block)

    ldbg.execute_blocks(md)

    captured = capsys.readouterr()
    # We expect to have been prompted and the code executed
    assert "Would you like to execute the following code block:" in captured.out
    assert executed["called"] is True
    assert "print('ran')" in executed["code"]


def test_execute_blocks_user_declines(monkeypatch, capsys):
    md = "```\nprint('should_not_run')\n```"
    # Simulate user input 'n'
    monkeypatch.setattr(builtins, "input", lambda prompt="": "n")
    executed = {"called": False}

    monkeypatch.setattr(
        ldbg, "execute_code_block", lambda code: executed.update(called=True)
    )

    ldbg.execute_blocks(md)
    captured = capsys.readouterr()
    assert "Would you like to execute the following code block:" in captured.out
    assert executed.get("called") is not True


def test_generate_commands_calls_api_and_forwards_response(monkeypatch, capsys):
    """
    Ensure generate_commands:
      - prints the system/user prompts when print_prompt=True
      - calls the client.chat.completions.create API
      - prints the model response and passes it to execute_blocks
    """
    # Create a fake response text that contains a code block
    fake_response_text = (
        "Here is a suggestion:\n\n```python\nprint('from model')\n```\n"
        "And a closing line."
    )

    # Spy object to verify execute_blocks received the model response
    called = {"create_called": False, "passed_response": None}

    def fake_create(*args, **kwargs):
        called["create_called"] = True
        # Build an object with the expected shape: .choices[0].message.content
        msg = types.SimpleNamespace(content=fake_response_text)
        choice = types.SimpleNamespace(message=msg)
        return types.SimpleNamespace(choices=[choice])

    # Patch the chain client.chat.completions.create
    monkeypatch.setattr(ldbg.client.chat.completions, "create", fake_create)

    # Patch execute_blocks to capture what is passed
    def fake_execute_blocks(resp_text):
        called["passed_response"] = resp_text

    monkeypatch.setattr(ldbg, "execute_blocks", fake_execute_blocks)

    # Call generate_commands from a real frame (the test's current frame) to let it build context
    frame = inspect.currentframe()
    # Run function
    ldbg.generate_commands("describe unknown_data", frame=frame, print_prompt=True)

    captured = capsys.readouterr()
    # Confirm we printed the System prompt and User prompt
    assert "System prompt:" in captured.out
    assert "User prompt:" in captured.out

    # Confirm the API stub was called and execute_blocks got the model response
    assert called["create_called"] is True
    assert called["passed_response"] == fake_response_text


def test_generate_commands_handles_none_response(monkeypatch, capsys):
    """
    If the API returns a response object with None content, generate_commands should return gracefully.
    """

    def fake_create_none(*args, **kwargs):
        msg = types.SimpleNamespace(content=None)
        choice = types.SimpleNamespace(message=msg)
        return types.SimpleNamespace(choices=[choice])

    monkeypatch.setattr(ldbg.client.chat.completions, "create", fake_create_none)
    # Patch execute_blocks to ensure it would not be called when response is None
    monkeypatch.setattr(
        ldbg,
        "execute_blocks",
        lambda t: (_ for _ in ()).throw(AssertionError("should not be called")),
    )

    # Call - should not raise
    ldbg.generate_commands(
        "any prompt", frame=inspect.currentframe(), print_prompt=False
    )

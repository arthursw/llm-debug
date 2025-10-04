import inspect
import textwrap
import traceback
import linecache
import os
from openai import OpenAI

if "OPENROUTER_API_KEY" in os.environ:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )
else:
    client = OpenAI()

def generate_commands(prompt, frame=None, model="gpt-5-mini-2025-08-07", code_only=False, print_prompt=True, print_answer=True):
    """
    Generate Python debug code based on natural-language instructions.

    Includes:
    - Call stack / traceback
    - Current function’s source
    - Surrounding source lines (like ipdb 'll')

    Example:
        code = generate_commands("describe my_data")
        exec(code, frame.f_globals, frame.f_locals)
    """
    if frame is None:
        frame = inspect.currentframe().f_back

    # Locals & globals preview
    locals_preview = {k: type(v).__name__ for k, v in frame.f_locals.items()}
    globals_preview = {k: type(v).__name__ for k, v in frame.f_globals.items()}

    # Traceback / call stack
    stack_summary = traceback.format_stack(frame)
    stack_text = "".join(stack_summary[-15:])  # limit to avoid overload

    # Current function source
    try:
        source_lines, start_line = inspect.getsourcelines(frame)
        func_source = "".join(source_lines)
    except (OSError, TypeError):
        func_source = "<source unavailable>"

    # Context like ipdb 'll'
    filename = frame.f_code.co_filename
    lineno = frame.f_lineno
    start_context = max(lineno - 10, 1)
    context_lines = []
    for i in range(start_context, lineno + 10):
        line = linecache.getline(filename, i)
        if line:
            context_lines.append(f"{i:4d}: {line}")
    context_text = "".join(context_lines)

    code_only_rule = "Do not print explanations; just produce the code." if code_only else ""

    context = textwrap.dedent(f"""
    You are a Python debugging assistant.
    The user is paused inside a Python script.

    Local variables and their types:
    {locals_preview}

    Global variables and their types:
    {globals_preview}

    Current call stack (traceback):
    {stack_text}

    Current function source:
    {func_source}

    Nearby code (like ipdb 'll'):
    {context_text}

    Your task: return **only Python code** (no prose) that can be executed 
    to inspect or debug the situation. You may import libraries if needed.
    {code_only_rule}
    """)

    if print_prompt:
        print("System prompt:")
        print(context)
        print("\nUser prompt:")
        print(prompt)

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": prompt}
        ],
        temperature=1
    )

    code = resp.choices[0].message.content
    
    if print_answer:
        print(code)

    return code.strip("`\n ")

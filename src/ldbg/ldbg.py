import inspect
import re
import textwrap
import traceback
import linecache
import os
import pprint
from types import FrameType
from typing import cast

from openai import OpenAI

LENGTH_MAX = 10000
CODE_BLOCK_REGEX = r'```(?:[\w+-]*)\n(.*?)```'

if "OPENROUTER_API_KEY" in os.environ:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )
else:
    client = OpenAI()

def extract_code_blocks(markdown_text: str):
    pattern = re.compile(CODE_BLOCK_REGEX, re.DOTALL)
    return pattern.findall(markdown_text)

def execute_code_block(code: str):
    exec(code, {})

def execute_blocks(markdown_text: str | None)-> None:
    """
    Extract the code blocks in the markdown and ask user if he wants to execute them
    """
    if markdown_text is None:
        return
    blocks = extract_code_blocks(markdown_text)
    for block in blocks:
        print("Would you like to execute the following code block:")
        print(textwrap.indent(block, "    "))
        confirm = input("(y/n)").lower()
        if confirm.lower() in ["yes", "y"]:
            execute_code_block(block)

def generate_commands(prompt:str, frame=None, model="gpt-5-mini-2025-08-07", print_prompt=True, length_max=LENGTH_MAX, context=""):
    """
    Generate Python debug help based on natural-language instructions.

    Includes:
    - Call stack / traceback
    - Current function’s source
    - Surrounding source lines (like ipdb 'll')

    Example:

    >>> import ldbg
    >>> ldbg.generate_commands("describe unknown_data")
    The model "gpt-5-mini-2025-08-07" answered:

        unknown_data is an numpy array which can be described with the following pandas code:
        
        ```
        pandas.DataFrame(unknown_data).describe()
        ```

        Note: you can use numpy.set_printoptions (or a library like numpyprint) to pretty print your array:
        
        ```
        with np.printoptions(precision=2, suppress=True, threshold=5):
            unknown_data
        ```

    Would you like to execute the following code block:
        pandas.DataFrame(unknown_data).describe()
    (y/n)?
    

    <<< user enters y
                  0
    count  9.000000
    mean   4.000000
    std    2.738613
    min    0.000000
    25%    2.000000
    50%    4.000000
    75%    6.000000
    max    8.000000

    
    Would you like to execute the following code block:
        with np.printoptions(precision=2, suppress=True, threshold=5):
            unknown_data
    (y/n)?

    <<< user enters n
    """
    if frame is None:
        frame = cast(FrameType, inspect.currentframe().f_back) # type: ignore

    # Locals & globals preview
    locals_preview = pprint.pformat(frame.f_locals)[:length_max] # {k: type(v).__name__ for k, v in frame.f_locals.items()}
    globals_preview = pprint.pformat(frame.f_globals)[:length_max] # {k: type(v).__name__ for k, v in frame.f_globals.items()}

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

    # ldbg.generate_commands({prompt}, model={model}, code_only={code_only}, print_prompt={print_prompt}, print_answer={print_answer}, length_max={length_max})
    context = textwrap.dedent(f"""
    You are a Python debugging assistant.
    The user is paused inside a Python script.
                              
    The user just ran `import ldbg; ldbg.gc({prompt}, model={model})` to ask you some help (gc stands for generate commands).

    Local variables and their types (`locals = pprint.pformat(inspect.currentframe().f_locals)[:length_max]`):
    {locals_preview}

    Global variables and their types (`globals = pprint.pformat(inspect.currentframe().f_globals)[:length_max]`):
    {globals_preview}

    Current call stack (traceback):
    {stack_text}

    Current function source:
    {func_source}

    Nearby code (like ipdb 'll'):
    {context_text}

    Additional context:
    {context}

    If you need more context, a more detailed view of the local variables or the content of a source file, 
    tell the user the commands he should run to print the details you need.

    For example, if you need to know more details about the local variables, tell him:

        I need more context to help you. 
        Could you execute the following commands to give me more context? They will provide the details I need to help you.

        ```
        import inspect
        frame = inspect.currentframe()
        # Get frame.f_locals with a depth of 2
        local_variables = pprint.pformat(frame.f_locals, depth=2)
        ```
    
        Then you can ask me again:
        ```
        ldbg.gc({prompt}, model={model}, context = f"local variables are: {{local_variables:.50000}}")
        ```

    Another example, if you need to know the content of some source files:

        I need more context to help you.
        Could you execute the following commands to give me more context? They will provide the details I need to help you.

        ```
        # Get the content of important.py
        import_file_path = list(Path().glob('**/important.py'))[0]

        with open(import_file_path) as f:
            important_content = f.read()
        
        # Find the lines surrounding the class ImportantClass in very_large_script.py
        search = "class ImportantClass"
        with open('path/to/important/very_large_script.py') as f:
            lines = f.readlines()
        
        # Find the 0-based index of the first matching line
        idx = next(i for i, line in enumerate(lines) if search in line)

        # Calculate start and end indices
        start = max(0, idx - 10)
        end = min(len(lines), idx + 10 + 1)

        # Get the surrounding lines
        script_content = []
        for i, line in enumerate(lines[start:end]):
            script_content.append(f"{{start + i + 1:04d}}: {{line.rstrip()}}")
        ```
    
        Then you can ask me again:
        ```
        ldbg.gc({prompt}, model={model}, context=f"important.py: {{important_content:.50000}}, very_large_script.py (lines {{start}} to {{end}}): {{script_content:.50000}}")
        ```

    You can also ask for help in multiple steps:

        Could you execute the following commands to give me more context? 
        This will tell me all the source files in the current working directory.

        ```
        import pathlib
        EXCLUDED = {{".venv", ".pixi"}}
        python_files = [str(p) for p in pathlib.Path('.').rglob('*.py') if not any(part in EXCLUDED for part in p.parts)]
        ```
    
        Then you can ask me again:
        ```
        ldbg.gc({prompt}, model={model}, context=f"the python files are: {{python_files:.50000}}")
        ```

        And then I will know more about the project, and I might ask you to execute more commands 
        (for example to read some important files) to get all the context I need.

    The length of your context window is limited and you perform better with focused questions and context. 
    Thus, when you ask the user to execute commands and send you more information, 
    always make sure to be precise so that you get a response of reasonable length. 
    For example, if you need some information in a huge file, 
    provide commands to extract exactly what you need instead of reading the entire file. 
    If you need a specific value deep in the locals values, get `frame.f_locals["deep_object"].deep_dict["deep_attribute"]["sub_attribute"]["etc"]`
    instead of getting the entire locals with a large depth as in `local_variables = pprint.pformat(frame.f_locals, depth=10)`.
    
    Cap the length of the responses to avoid reaching the maximum prompt length (which would result in a failure). 
    
    The user is a developer, you can also ask him details about the context in natural language.

    If you have all the context you need, just provide a useful answer.
    For example, if the user asks "describe unknown_data", you could answer:

        `unknown_data` is an numpy array which can be described with the following pandas code:
        
        ```
        pandas.DataFrame(unknown_data).describe()
        ```

        You could also use numpy.set_printoptions (or a library like numpyprint) to pretty print your array:
        
        ```
        with np.printoptions(precision=2, suppress=True, threshold=5):
            unknown_data
        ```

    Always put the code to execute in triple backticks code blocks.
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

    response = resp.choices[0].message.content
    
    if print_prompt:
        print("\n\n\n")
    
    if response is None:
        return
    
    print(f"Model {model} says:")
    print(textwrap.indent(response, "    "))

    execute_blocks(response)

    return

gc = generate_commands
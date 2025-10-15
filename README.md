# llm-debug

### A Minimal Python Library to debug with LLMs

Use natural-language prompts while debugging. Prompts are augmented with your current stack, variables, and source context.

DO NOT USE THIS LIBRARY

> “AI everywhere is rocket engines on a skateboard: a thrill that ends in wreckage. The planet pays in energy and emissions, and we pay in something subtler — the slow atrophy of our own intelligence, left idle while the machines do the heavy lifting.” ChatGPT

## Features

- 🐍 Generate Python debug commands from natural-language instructions.
- 🔍 Context-aware: prompt auto-includes call stack, local/global variable previews, current function - source, and nearby code.
- ⚡ Works like an AI-augmented pdb: just ask what you want to inspect.
- 🤖 Supports OpenRouter

## Installation

`pip install ldbg`

## Quick Start

### Example Session

```python

>>> unknown_data = np.arange(9)
>>> example_dict = {"a": 1, "b": [1, 2, 3]}
>>> example_numbers = list(range(10))
>>> import ldbg
>>> ldbg.gc("describe unknown_data")
The model "gpt-5-mini-2025-08-07" says:

    unknown_data is an numpy array which can be described with the following pandas code:
    
    ```code block 1
    pandas.DataFrame(unknown_data).describe()
    ```

    Note: you can use numpy.set_printoptions (or a library like numpyprint) to pretty print your array:
    
    ```code block 2
    with np.printoptions(precision=2, suppress=True, threshold=5):
        unknown_data
    ```

Would you like to execute the following code block:
    pandas.DataFrame(unknown_data).describe()
(y/n)
```

User enters y:
```
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
(y/n)
```

User enters n and continues:

```python
>>> ldbg.gc("plot example_numbers as a bar chart")
The model "gpt-5-mini-2025-08-07" says:

    ```
    import matplotlib.pyplot as plt
    plt.bar(range(len(numbers)), numbers)
    plt.show()
    ```

Would you like to execute the following code block:
...
```

### Example natural-language prompts

- "Describe my numpy arrays"
- "plot my_data['b'] as a histogram"
- "give me an example pandas dataframe about employees"
- "generate a 3x10x12 numpy array which will be used as an example image"
- "convert this Pillow image to grayscale"
- "open this 'image.ome.tiff' with bioio"

## Configuration

By default, llm-debug uses the OpenAI client. So it reads the [OPENAI_API_KEY environment variable](https://platform.openai.com/docs/quickstart).

To use OpenRouter instead, define the `OPENROUTER_API_KEY` environment variable:

`export OPENROUTER_API_KEY="your_api_key_here"`

## License

MIT License.
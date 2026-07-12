# Tools

openbrain supports function calling via Ollama's native tool API. Tools are
defined as Python functions with JSON Schema descriptions, registered in a
dispatch dict, and exposed to the model through the `tools` parameter in chat
requests.

## How Tool Calling Works

```
User message → Ollama (with tools list) → model requests tool_call
                                                ↓
                                          execute tool function
                                                ↓
                                          append tool result as message
                                                ↓
                                          Ollama with full conversation
                                                ↓
                                          final text response
```

The model may call zero, one, or multiple tools in a single turn. Tools are
executed and their results fed back to the model, which then produces a natural
language answer. This loop runs up to 10 iterations to prevent infinite
tool-calling chains.

## Available Tools

### `web_search`

Search the web for current information using DuckDuckGo.

| Property | Description |
|---|---|
| **Name** | `web_search` |
| **Description** | Search the web for current information, news, docs, or anything the model doesn't know |
| **Backend** | `ddgs` library (free, no API key required) |
| **Dependency** | `ddgs>=9.14.4` |

#### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `query` | string | yes | — | Search query |
| `num_results` | integer | no | 5 | Number of results (1–10) |

### `sympy_calc`

Perform symbolic calculus and algebra using SymPy — differentiation,
integration, limits, series expansion, solving equations (including ODEs),
complex analysis, and expression simplification.

| Property | Description |
|---|---|
| **Name** | `sympy_calc` |
| **Description** | Symbolic math via SymPy for calculus, algebra, complex analysis |
| **Backend** | `sympy` library |
| **Dependency** | `sympy>=1.13` |

#### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `operation` | string | yes | — | One of: `diff`, `integrate`, `limit`, `series`, `solve`, `dsolve`, `simplify`, `expand`, `factor`, `apart`, `together`, `trigsimp`, `powsimp`, `summation`, `product`, `complex` |
| `expression` | string | yes | — | Math expression (e.g. `'x**2+1'`, `'sin(x)*cos(x)'`) |
| `variable` | string | no | `x` | Variable(s), comma-separated |
| `order` | integer | no | `1` | Derivative order, series terms, sum/product bound |
| `limit_point` | string | no | — | Limit point (`'oo'` for infinity) |
| `direction` | string | no | — | `'+'` / `'-'` / `''` (two-sided limit) |
| `series_point` | string | no | `0` | Series expansion point |
| `complex_operation` | string | no | — | For `operation=complex`: `re`, `im`, `conjugate`, `abs`, `arg`, `expand` |
| `output_format` | string | no | `pretty` | `pretty`, `latex`, or `repr` |

#### Examples

| Example | Result |
|---|---|
| `diff(x**2 + 2*x + 1)` | `2*x + 2` |
| `integrate(cos(x))` | `sin(x)` |
| `limit(1/x, at oo)` | `0` |
| `series(sin(x), order=5)` | `x**5/120 - x**3/6 + x` |
| `solve(x**2 - 4)` | `[-2, 2]` |
| `dsolve(f''(x) + f(x) = 0)` | `f(x) = C1*sin(x) + C2*cos(x)` |
| `simplify(sin(x)^2 + cos(x)^2)` | `1` |
| `complex(2 + 3*I, op=re)` | `2` |

### `sympy_plot`

Render a mathematical function as an ASCII plot in the terminal.

| Property | Description |
|---|---|
| **Name** | `sympy_plot` |
| **Description** | Plot single-variable functions as terminal ASCII art |
| **Backend** | `plotext` + `sympy.lambdify` |
| **Dependency** | `plotext>=5.3` |

#### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `expression` | string | yes | — | Function to plot (e.g. `'x**2'`, `'sin(x)'`) |
| `variable` | string | no | `x` | Independent variable name |
| `x_min` | number | no | `-10` | Minimum x-axis value |
| `x_max` | number | no | `10` | Maximum x-axis value |
| `y_min` | number | no | — | Minimum y-axis value (auto if omitted) |
| `y_max` | number | no | — | Maximum y-axis value (auto if omitted) |
| `title` | string | no | — | Optional plot title |

#### Example

```
User: Plot the function y = sin(x) between -π and π

Tool call: sympy_plot(expression="sin(x)", variable="x", x_min=-3.14, x_max=3.14)
Tool result: [ASCII plot showing a sine wave]

Assistant: Here's the plot of sin(x):
           (ASCII plot displayed inline)
```

### `linear_algebra`

Perform linear algebra operations on matrices and vectors.

| Property | Description |
|---|---|
| **Name** | `linear_algebra` |
| **Description** | Determinant, inverse, eigenvalues, RREF, rank, nullspace, charpoly, trace, transpose, Gram-Schmidt, LU/QR decomposition, solve linear systems, matrix arithmetic |
| **Backend** | `sympy.Matrix` |
| **Dependency** | `sympy>=1.13` |

#### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `operation` | string | yes | — | `det`, `inverse`, `eigenvals`, `eigenvects`, `rref`, `rank`, `nullspace`, `charpoly`, `trace`, `transpose`, `gram_schmidt`, `lu`, `qr`, `solve`, `multiply`, `add` |
| `matrix` | string | yes | — | Matrix in list-of-lists format (e.g. `'[[1,2],[3,4]]'`) |
| `matrix2` | string | no | — | Second matrix for `multiply` / `add` |
| `vector` | string | no | — | RHS vector for `solve`, or vector list for `gram_schmidt` (e.g. `'[1,2,3]'` or `'[[1,1],[1,-1]]'`) |

#### Examples

| Example | Result |
|---|---|
| `det([[1,2],[3,4]])` | `-2` |
| `inverse([[1,2],[3,4]])` | `[[-2, 1], [1.5, -0.5]]` |
| `eigenvals([[1,2],[3,4]])` | `{5/2 - sqrt(33)/2: 1, ...}` |
| `rref([[1,2,3],[4,5,6]])` | RREF + pivot columns |

### `stats_calc`

Probability and statistics calculations using common distributions.

| Property | Description |
|---|---|
| **Name** | `stats_calc` |
| **Description** | PDF, expectation, variance, std, probability queries, CDF, sampling, conditional expectation |
| **Backend** | `sympy.stats` |
| **Dependency** | `sympy>=1.13` |

#### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `operation` | string | yes | — | `density`, `expectation`, `variance`, `std`, `probability`, `cdf`, `sample`, `conditional` |
| `distribution` | string | yes | — | `Normal`, `Binomial`, `Poisson`, `Exponential`, `Uniform`, `Beta`, `Gamma`, `ChiSquared`, `Bernoulli`, `DiscreteUniform` |
| `params` | string | yes | — | JSON object of distribution parameters. See table below. |
| `expression` | string | no | — | Condition for probability (e.g. `'X > 3'`), value for CDF, or sample count |

#### Distribution Parameters

| Distribution | JSON keys |
|---|---|
| Normal | `{"mean": 0, "std": 1}` |
| Binomial | `{"n": 10, "p": 0.5}` |
| Poisson | `{"lam": 3}` |
| Exponential | `{"rate": 1}` |
| Uniform | `{"min": 0, "max": 1}` |
| Beta | `{"alpha": 2, "beta": 3}` |
| Gamma | `{"k": 2, "theta": 1}` |
| ChiSquared | `{"k": 5}` |
| Bernoulli | `{"p": 0.5}` |
| DiscreteUniform | `{"min": 1, "max": 6}` |

#### Examples

```
User: What's the probability that a standard normal exceeds 1.96?

Tool call: stats_calc(operation="probability", distribution="Normal",
                      params='{"mean":0,"std":1}', expression="X > 1.96")
Tool result: 0.024997... (≈ 0.025)

Assistant: P(Z > 1.96) ≈ 0.025 for a standard normal distribution.
```

```
User: What's the expected value of Binomial(10, 0.5)?

Tool call: stats_calc(operation="expectation", distribution="Binomial",
                      params='{"n":10,"p":0.5}')
Tool result: 5.0
```

### `physics_constants`

Look up fundamental physical constants with their SI values and dimensions.

| Property | Description |
|---|---|
| **Name** | `physics_constants` |
| **Description** | Lookup physical constants with numerical values and units |
| **Backend** | `sympy.physics.units` |
| **Dependency** | `sympy>=1.13` |

#### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | string | yes | — | Constant name (e.g. `speed_of_light`, `planck`) |
| `output_unit` | string | no | — | Optional unit to convert into (e.g. `'km/s'`) |

#### Available Constants

`speed_of_light`, `gravitational_constant`, `planck`, `hbar`, `boltzmann_constant`, `avogadro_constant`, `avogadro_number`, `electron_rest_mass`, `elementary_charge`, `vacuum_permittivity`, `vacuum_permeability`, `vacuum_impedance`, `stefan_boltzmann_constant`, `molar_gas_constant`, `faraday_constant`, `coulomb_constant`, `electronvolt`, `atomic_mass_unit`, `amu`, `planck_length`, `planck_time`, `planck_mass`, `planck_temperature`, `planck_charge`, `planck_energy`, `planck_force`, `planck_power`, `planck_pressure`, `planck_density`, `planck_current`, `planck_voltage`, `planck_impedance`, `planck_acceleration`, `planck_angular_frequency`, `planck_intensity`, `planck_energy_density`, `planck_momentum`, `planck_area`, `planck_volume`

#### Examples

```
User: What is the speed of light in km/s?

Tool call: physics_constants(name="speed_of_light", output_unit="km/s")
Tool result: Speed Of Light = 299792.458 km/s

Assistant: The speed of light is 299,792.458 km/s.
```

### `unit_converter`

Convert values between different units with dimensional analysis.

| Property | Description |
|---|---|
| **Name** | `unit_converter` |
| **Description** | Convert between units (SI, imperial, time, etc.) |
| **Backend** | `sympy.physics.units.convert_to` |
| **Dependency** | `sympy>=1.13` |

#### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `value` | string | yes | — | Numerical value (e.g. `'5'`, `'3.14'`) |
| `from_unit` | string | yes | — | Source unit (e.g. `'km'`, `'cm'`, `'hour'`, `'miles'`) |
| `to_unit` | string | yes | — | Target unit (e.g. `'miles'`, `'inches'`, `'second'`) |

#### Examples

| Input | Result |
|---|---|
| `5 km → miles` | ≈ 3.107 miles |
| `100 cm → inches` | ≈ 39.37 inches |
| `2 hours → seconds` | 7200 seconds |
| `1000 g → kg` | 1 kg |
| `1 lightyear → km` | ≈ 9.461 × 10¹² km |

### `calculate`

Evaluate a numerical expression and return the result. Supports arithmetic,
trigonometry, logarithms, constants, and common math functions. Use this for
quick numeric calculations instead of writing a full Python program.

| Property | Description |
|---|---|
| **Name** | `calculate` |
| **Description** | Evaluate a numerical expression using Python's math module |
| **Backend** | `eval()` with a restricted namespace (only math functions + constants) |

#### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `expression` | string | yes | — | Numerical expression to evaluate |

#### Supported Functions & Constants

| Category | Names |
|---|---|
| **Arithmetic** | `+`, `-`, `*`, `/`, `**`, `//`, `%`, parentheses |
| **Trig** | `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`, `sinh`, `cosh`, `tanh` |
| **Log/Exp** | `log`, `log10`, `log2`, `exp` |
| **Misc** | `sqrt`, `abs`, `floor`, `ceil`, `factorial`, `degrees`, `radians` |
| **Constants** | `pi`, `e`, `tau`, `inf` |

#### Examples

```
User: What is sin(pi/4)?

Tool call: calculate(expression="sin(pi/4)")
Tool result: 0.7071067811865476

Assistant: sin(π/4) = √2/2 ≈ 0.7071.
```

```
User: What's 2^10 + sqrt(144)?

Tool call: calculate(expression="2**10 + sqrt(144)")
Tool result: 1036.0

Assistant: 2^10 = 1024, sqrt(144) = 12, so 1024 + 12 = 1036.
```

```
User: How many digits in 100! ?

Tool call: calculate(expression="log10(factorial(100))")
Tool result: 157.97000365471575

Assistant: 100! has 158 digits (floor of log10(100!) + 1).
```

### `run_python`

Execute a simple Python program in a sandboxed environment. Designed for
brute-force search, combinatorial enumeration, numerical simulation, and
algorithmic computation.

| Property | Description |
|---|---|
| **Name** | `run_python` |
| **Description** | Execute Python code in a sandbox with timeout for brute-force, enumeration, simulation |
| **Backend** | `exec()` with restricted builtins and module whitelist |
| **Timeout** | 30 seconds |

#### Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `code` | string | yes | — | Python code to execute. Must use `print()` to produce output. |

#### Allowed Modules

`math`, `itertools`, `collections`, `random`, `statistics`, `json`, `re`, `fractions`, `decimal`, `typing`, `hashlib`, `bisect`, `heapq`, `functools`, `string`, `time`, `copy`, `enum`, `dataclasses`, `pprint`

#### Security

- Runs in a sandbox with restricted builtins (no file I/O, no `os`/`subprocess`/`sys`)
- Only the whitelisted modules above can be imported
- 30-second timeout enforced via `SIGALRM`
- stdout is captured and returned

#### Examples

```
User: Find all 3-digit numbers where the sum of cubes of digits equals the number itself.

Tool call: run_python(code="for i in range(100, 1000):\n    a, b, c = i // 100, (i // 10) % 10, i % 10\n    if a**3 + b**3 + c**3 == i:\n        print(i)")
Tool result: 153
             370
             371
             407

Assistant: The Armstrong numbers (narcissistic numbers) between 100 and 999 are 153, 370, 371, and 407.
```

```
User: How many ways can you make 10 cents using pennies, nickels, and dimes?

Tool call: run_python(code="count = 0\nfor p in range(11):\n    for n in range(3):\n        for d in range(2):\n            if p + 5*n + 10*d == 10:\n                count += 1\n                print(f'p={p}, n={n}, d={d}')\nprint(f'Total: {count}')")
Tool result: p=0, n=0, d=1
             p=0, n=2, d=0
             p=5, n=1, d=0
             p=10, n=0, d=0
             Total: 4

Assistant: There are 4 ways to make 10 cents using pennies, nickels, and dimes.
```

## Adding a New Tool

1. Install any required dependency.
2. Define the tool schema in `openbrain/tools.py` in the `TOOLS` list.
3. Implement the async function in the same file.
4. Register it in `TOOL_DISPATCH[function_name]`.

```python
TOOLS.append({
    "type": "function",
    "function": {
        "name": "my_tool",
        "description": "What this tool does",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "Description of param1"
                }
            },
            "required": ["param1"]
        }
    }
})

async def my_tool(param1: str) -> str:
    # implement
    return result

TOOL_DISPATCH["my_tool"] = my_tool
```

The schema follows the [OpenAI function calling format][openai-tools], which
Ollama also uses.

[openai-tools]: https://platform.openai.com/docs/guides/function-calling

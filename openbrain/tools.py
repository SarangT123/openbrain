import io
import sys
from ddgs import DDGS
from sympy import (
    sympify, Symbol, diff, integrate, limit, series,
    simplify, expand, factor, solve, dsolve, summation, product,
    oo, re, im, conjugate, Abs, arg, latex, pretty,
    Eq, apart, together, trigsimp, powsimp, Function,
    Matrix, GramSchmidt,
    lambdify,
)
from sympy.core.function import AppliedUndef

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information. Use this for real-time data, news, documentation, or anything the model doesn't know about.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return (1-10)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sympy_calc",
            "description": "Perform symbolic calculus and algebra using SymPy. Supports differentiation, integration, limits, series expansion, solving equations (including ODEs), complex analysis, and expression simplification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "The calculus operation to perform",
                        "enum": [
                            "diff",
                            "integrate",
                            "limit",
                            "series",
                            "solve",
                            "dsolve",
                            "simplify",
                            "expand",
                            "factor",
                            "apart",
                            "together",
                            "trigsimp",
                            "powsimp",
                            "summation",
                            "product",
                            "complex"
                        ]
                    },
                    "expression": {
                        "type": "string",
                        "description": "The mathematical expression as a string (e.g. 'x**2 + 2*x + 1', 'sin(x)*cos(x)', 'f(x).diff(x, x) + f(x)'). Use ** for powers, / for division, * for multiplication."
                    },
                    "variable": {
                        "type": "string",
                        "description": "The variable(s) to operate on, comma-separated for multiple (e.g. 'x' or 'x,y'). Defaults to 'x'."
                    },
                    "order": {
                        "type": "integer",
                        "description": "Order for differentiation (default: 1), series expansion terms, or summation/product terms."
                    },
                    "limit_point": {
                        "type": "string",
                        "description": "The point for limit evaluation (e.g. '0', 'oo', '-oo'). Use 'oo' for infinity."
                    },
                    "direction": {
                        "type": "string",
                        "description": "Direction for limits: '+' for right-hand, '-' for left-hand, '' for two-sided.",
                        "enum": ["", "+", "-"]
                    },
                    "complex_operation": {
                        "type": "string",
                        "description": "For operation='complex': 're' (real part), 'im' (imaginary part), 'conjugate', 'abs' (modulus), 'arg' (argument/phase), 'expand' (expand complex expression)."
                    },
                    "series_point": {
                        "type": "string",
                        "description": "The point for series expansion (default: '0')."
                    },
                    "output_format": {
                        "type": "string",
                        "description": "Output format: 'pretty' (readable text), 'latex' (LaTeX), 'repr' (Python repr). Default: 'pretty'.",
                        "enum": ["pretty", "latex", "repr"]
                    }
                },
                "required": ["operation", "expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sympy_plot",
            "description": "Render a mathematical function as an ASCII plot in the terminal using plotext. Great for visualizing single-variable functions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The function to plot (e.g. 'x**2', 'sin(x)', 'cos(x) + 2')."
                    },
                    "variable": {
                        "type": "string",
                        "description": "The independent variable (default: 'x')."
                    },
                    "x_min": {
                        "type": "number",
                        "description": "Minimum x-axis value (default: -10)."
                    },
                    "x_max": {
                        "type": "number",
                        "description": "Maximum x-axis value (default: 10)."
                    },
                    "y_min": {
                        "type": "number",
                        "description": "Minimum y-axis value (auto-scaled if not set)."
                    },
                    "y_max": {
                        "type": "number",
                        "description": "Maximum y-axis value (auto-scaled if not set)."
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional title for the plot."
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "linear_algebra",
            "description": "Perform linear algebra operations on matrices and vectors using SymPy. Supports determinant, inverse, eigenvalues, eigenvectors, RREF, rank, nullspace, characteristic polynomial, trace, transpose, Gram-Schmidt, LU/Q R decomposition, solving linear systems, and matrix arithmetic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "The linear algebra operation to perform.",
                        "enum": [
                            "det", "inverse", "eigenvals", "eigenvects",
                            "rref", "rank", "nullspace", "charpoly",
                            "trace", "transpose", "gram_schmidt",
                            "lu", "qr", "solve", "multiply", "add"
                        ]
                    },
                    "matrix": {
                        "type": "string",
                        "description": "The matrix as a string in list-of-lists format (e.g. '[[1,2],[3,4]]')."
                    },
                    "matrix2": {
                        "type": "string",
                        "description": "Second matrix for multiply/add operations (same format as matrix)."
                    },
                    "vector": {
                        "type": "string",
                        "description": "Vector(s) for Gram-Schmidt or solve as a string (e.g. '[1,2,3]' or '[[1,2],[1,0]]')."
                    }
                },
                "required": ["operation", "matrix"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "stats_calc",
            "description": "Perform probability and statistics calculations using SymPy. Supports probability density functions, expectation, variance, standard deviation, probability queries, CDF, sampling, and conditional probability for common distributions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "The statistics operation to perform.",
                        "enum": [
                            "density", "expectation", "variance", "std",
                            "probability", "cdf", "sample", "conditional"
                        ]
                    },
                    "distribution": {
                        "type": "string",
                        "description": "The probability distribution to use.",
                        "enum": [
                            "Normal", "Binomial", "Poisson", "Exponential",
                            "Uniform", "Beta", "Gamma", "ChiSquared",
                            "Bernoulli", "DiscreteUniform"
                        ]
                    },
                    "params": {
                        "type": "string",
                        "description": "Distribution parameters as a JSON object string. Examples: Normal: '{\"mean\":0,\"std\":1}'. Binomial: '{\"n\":10,\"p\":0.5}'. Poisson: '{\"lam\":3}'. Exponential: '{\"rate\":1}'. Uniform: '{\"min\":0,\"max\":1}'. Beta: '{\"alpha\":2,\"beta\":3}'. Gamma: '{\"k\":2,\"theta\":1}'. ChiSquared: '{\"k\":5}'. Bernoulli: '{\"p\":0.5}'. DiscreteUniform: '{\"min\":1,\"max\":6}'."
                    },
                    "expression": {
                        "type": "string",
                        "description": "For operation='probability': a condition string (e.g. 'X > 3', 'X <= 5', 'X > 2 & X < 8'). For operation='conditional': a condition string (e.g. 'X > 0'). For operation='density': leave empty. For operation='cdf': a value (e.g. '1.5'). For operation='sample': number of samples (integer string)."
                    }
                },
                "required": ["operation", "distribution", "params"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "physics_constants",
            "description": "Look up fundamental physical constants and their values. Includes speed of light, gravitational constant, Planck's constant, Boltzmann constant, Avogadro constant, electron mass, elementary charge, vacuum permittivity/permeability, Stefan-Boltzmann constant, gas constant, and more.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the physical constant. Options: speed_of_light, gravitational_constant, planck, hbar, boltzmann_constant, avogadro_constant, avogadro_number, electron_rest_mass, elementary_charge, vacuum_permittivity, vacuum_permeability, vacuum_impedance, stefan_boltzmann_constant, molar_gas_constant, faraday_constant, coulomb_constant, electronvolt, atomic_mass_unit, amu, planck_length, planck_time, planck_mass, planck_temperature, planck_charge, planck_energy, planck_force, planck_power, planck_pressure, planck_density, planck_current, planck_voltage, planck_impedance, planck_acceleration, planck_angular_frequency, planck_intensity, planck_energy_density, planck_momentum, planck_area, planck_volume."
                    },
                    "output_unit": {
                        "type": "string",
                        "description": "Optional unit to convert the constant into (e.g. 'km/s' for speed_of_light)."
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "unit_converter",
            "description": "Convert a value from one unit to another using SymPy's unit system. Supports SI units, imperial units, time, temperature, and more. Examples: 5 km -> miles, 100 cm -> inches, 2 hours -> seconds, 300 K -> degC.",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {
                        "type": "string",
                        "description": "The numerical value to convert (e.g. '5' or '3.14')."
                    },
                    "from_unit": {
                        "type": "string",
                        "description": "The source unit (e.g. 'km', 'cm', 'hour', 'kg', 'miles', 'degF')."
                    },
                    "to_unit": {
                        "type": "string",
                        "description": "The target unit (e.g. 'miles', 'inches', 'second', 'g', 'meter')."
                    }
                },
                "required": ["value", "from_unit", "to_unit"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a numerical expression and return the result. Supports arithmetic (+, -, *, /, **, //, %), trig (sin, cos, tan, asin, acos, atan, atan2), log/exp (log, log10, log2, exp), constants (pi, e, tau, inf), sqrt, abs, floor, ceil, factorial, degrees/radians, and parentheses. Use this for quick numeric calculations instead of writing a full Python program.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "A numerical expression to evaluate (e.g. 'sin(pi/4)', 'sqrt(144) + 3*7', 'log(100, 10)', '2**10', 'factorial(5)'). Uses Python's math module under the hood."
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Execute a simple Python program and return its output. Use this for brute-force search, combinatorial enumeration, numerical simulation, or any algorithmic computation. The code runs in a sandbox with a 30-second timeout. Available modules: math, itertools, collections, random, statistics, json, re, fractions, decimal, typing, hashlib, bisect, heapq, functools, string, time, copy, enum, dataclasses, pprint. Use print() to produce output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python code to execute. Must use print() to produce output. The code is executed with a 30-second timeout. Available modules: math, itertools, collections, random, statistics, json, re, fractions, decimal, typing, hashlib, bisect, heapq, functools, string, time, copy, enum, dataclasses, pprint."
                    }
                },
                "required": ["code"]
            }
        }
    },
]

TOOL_DISPATCH: dict[str, callable] = {}


# ---------------------------------------------------------------------------
# web_search
# ---------------------------------------------------------------------------

async def web_search(query: str, num_results: int = 5) -> str:
    num_results = max(1, min(10, num_results))
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))
        if not results:
            return "No results found."
        lines = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "")
            body = r.get("body", "")
            href = r.get("href", "")
            lines.append(f"{i}. {title}\n   {body}\n   {href}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"Search failed: {e}"

TOOL_DISPATCH["web_search"] = web_search


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_SYMPY_CACHED_SYMBOLS: dict[str, Symbol] = {}


def _get_sympy_symbols(variables: str | None) -> tuple:
    if not variables:
        return (Symbol("x"),)
    result = []
    for v in variables.replace(" ", "").split(","):
        if v not in _SYMPY_CACHED_SYMBOLS:
            _SYMPY_CACHED_SYMBOLS[v] = Symbol(v)
        result.append(_SYMPY_CACHED_SYMBOLS[v])
    return tuple(result)


# ---------------------------------------------------------------------------
# sympy_calc
# ---------------------------------------------------------------------------

async def sympy_calc(
    operation: str,
    expression: str,
    variable: str = "x",
    order: int = 1,
    limit_point: str = "",
    direction: str = "",
    series_point: str = "0",
    complex_operation: str = "",
    output_format: str = "pretty",
) -> str:
    try:
        syms = _get_sympy_symbols(variable)
        expr = sympify(expression)

        if operation == "diff":
            var = syms[0] if len(syms) == 1 else syms
            result = diff(expr, var, order)

        elif operation == "integrate":
            var = syms[0] if len(syms) == 1 else syms
            result = integrate(expr, var)

        elif operation == "limit":
            pt = sympify(limit_point) if limit_point else 0
            var = syms[0]
            if direction == "+":
                result = limit(expr, var, pt, dir="+")
            elif direction == "-":
                result = limit(expr, var, pt, dir="-")
            else:
                result = limit(expr, var, pt)

        elif operation == "series":
            pt = sympify(series_point)
            var = syms[0]
            result = series(expr, var, pt, order + 1).removeO()

        elif operation == "solve":
            result = solve(expr, *syms)

        elif operation == "dsolve":
            funcs = list(expr.atoms(AppliedUndef))
            if not funcs:
                return "No undefined function found in expression."
            f = funcs[0]
            if isinstance(expr, Eq):
                result = dsolve(expr, f)
            else:
                result = dsolve(Eq(expr, 0), f)

        elif operation == "simplify":
            result = simplify(expr)

        elif operation == "expand":
            result = expand(expr)

        elif operation == "factor":
            result = factor(expr)

        elif operation == "apart":
            var = syms[0]
            result = apart(expr, var)

        elif operation == "together":
            result = together(expr)

        elif operation == "trigsimp":
            result = trigsimp(expr)

        elif operation == "powsimp":
            result = powsimp(expr)

        elif operation == "summation":
            var = syms[0]
            result = summation(expr, (var, 1, order))

        elif operation == "product":
            var = syms[0]
            result = product(expr, (var, 1, order))

        elif operation == "complex":
            expr_sym = sympify(expression)
            if complex_operation == "re":
                result = re(expr_sym)
            elif complex_operation == "im":
                result = im(expr_sym)
            elif complex_operation == "conjugate":
                result = conjugate(expr_sym)
            elif complex_operation == "abs":
                result = Abs(expr_sym)
            elif complex_operation == "arg":
                result = arg(expr_sym)
            elif complex_operation == "expand":
                result = expand(expr_sym)
            else:
                return f"Unknown complex_operation '{complex_operation}'. Use: re, im, conjugate, abs, arg, expand."
        else:
            return f"Unknown operation '{operation}'."

        if output_format == "latex":
            return f"$$ {latex(result)} $$"
        elif output_format == "repr":
            return repr(result)
        else:
            return pretty(result)

    except Exception as e:
        return f"SymPy error: {e}"

TOOL_DISPATCH["sympy_calc"] = sympy_calc


# ---------------------------------------------------------------------------
# sympy_plot
# ---------------------------------------------------------------------------

async def sympy_plot(
    expression: str,
    variable: str = "x",
    x_min: float = -10,
    x_max: float = 10,
    y_min: float | None = None,
    y_max: float | None = None,
    title: str = "",
) -> str:
    try:
        import plotext as plt

        sym = Symbol(variable)
        expr = sympify(expression)
        f = lambdify(sym, expr, modules="numpy")

        points = 200
        xs = [x_min + (x_max - x_min) * i / (points - 1) for i in range(points)]
        ys = []

        for x in xs:
            try:
                val = float(f(x))
                if val > 1e30 or val < -1e30 or val != val:
                    ys.append(None)
                else:
                    ys.append(val)
            except Exception:
                ys.append(None)

        valid_ys = [y for y in ys if y is not None]
        if not valid_ys:
            return "Could not evaluate function — no valid points found."

        if y_min is not None and y_max is not None:
            plt.ylim(y_min, y_max)

        plt.clear_figure()
        plt.plot(xs, [y if y is not None else None for y in ys])
        if title:
            plt.title(title)
        else:
            plt.title(f"y = {expression}")

        plt.xlabel(variable)
        plt.ylabel("y")

        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        plt.show()
        sys.stdout = old
        plot_str = buf.getvalue()

        return plot_str

    except Exception as e:
        return f"Plot error: {e}"

TOOL_DISPATCH["sympy_plot"] = sympy_plot


# ---------------------------------------------------------------------------
# linear_algebra
# ---------------------------------------------------------------------------

async def linear_algebra(
    operation: str,
    matrix: str,
    matrix2: str = "",
    vector: str = "",
) -> str:
    try:
        M = Matrix(sympify(matrix))
        if not M.is_Matrix:
            return "Input must be a matrix."

        if operation == "det":
            result = M.det()

        elif operation == "inverse":
            if M.is_square:
                result = M.inv()
            else:
                return "Matrix must be square for inverse."

        elif operation == "eigenvals":
            ev = M.eigenvals()
            result = ev

        elif operation == "eigenvects":
            ev = M.eigenvects()
            lines = []
            for val, mult, vecs in ev:
                for v in vecs:
                    lines.append(f"lambda={pretty(val)}, mult={mult}: {pretty(v)}")
            return "\n".join(lines)

        elif operation == "rref":
            r, pivots = M.rref()
            return f"RREF:\n{pretty(r)}\npivot columns: {pivots}"

        elif operation == "rank":
            result = M.rank()

        elif operation == "nullspace":
            ns = M.nullspace()
            if ns:
                lines = []
                for i, v in enumerate(ns):
                    lines.append(f"v{i}: {pretty(v)}")
                return "\n".join(lines)
            return "Nullspace contains only the zero vector."

        elif operation == "charpoly":
            lam = Symbol("lambda")
            result = M.charpoly(lam)

        elif operation == "trace":
            result = M.trace()

        elif operation == "transpose":
            result = M.T

        elif operation == "gram_schmidt":
            vecs_input = sympify(vector)
            if isinstance(vecs_input, list):
                vecs_list = [Matrix(v) if isinstance(v, list) else v for v in vecs_input]
            else:
                return "Provide vectors as a list of lists (e.g. '[[1,1],[1,-1]]')."
            gs = GramSchmidt(vecs_list)
            result = Matrix(gs)

        elif operation == "lu":
            L, U, perm = M.LUdecomposition()
            return f"L:\n{pretty(L)}\n\nU:\n{pretty(U)}\n\npermutation: {perm}"

        elif operation == "qr":
            Q, R = M.QRdecomposition()
            return f"Q:\n{pretty(Q)}\n\nR:\n{pretty(R)}"

        elif operation == "solve":
            b_vec = Matrix(sympify(vector)) if vector else None
            if b_vec is None:
                return "Provide a vector for the RHS of Ax = b."
            result = M.LUsolve(b_vec)

        elif operation == "multiply":
            if not matrix2:
                return "Provide matrix2 for multiplication."
            M2 = Matrix(sympify(matrix2))
            result = M * M2

        elif operation == "add":
            if not matrix2:
                return "Provide matrix2 for addition."
            M2 = Matrix(sympify(matrix2))
            result = M + M2

        else:
            return f"Unknown operation '{operation}'."

        return pretty(result)

    except Exception as e:
        return f"Linear algebra error: {e}"

TOOL_DISPATCH["linear_algebra"] = linear_algebra


# ---------------------------------------------------------------------------
# stats_calc
# ---------------------------------------------------------------------------

async def stats_calc(
    operation: str,
    distribution: str,
    params: str,
    expression: str = "",
) -> str:
    try:
        import json
        from sympy.stats import (
            Normal, Binomial, Poisson, Exponential, Uniform,
            Beta, Gamma, ChiSquared, Bernoulli, DiscreteUniform,
            density, E, variance, std, P, cdf, sample, given,
        )

        dist_info = {
            "Normal": (Normal, {"mean": "mean", "std": "std"}),
            "Binomial": (Binomial, {"n": "n", "p": "p"}),
            "Poisson": (Poisson, {"lam": "lamda"}),
            "Exponential": (Exponential, {"rate": "rate"}),
            "Uniform": (Uniform, {"min": "left", "max": "right"}),
            "Beta": (Beta, {"alpha": "alpha", "beta": "beta"}),
            "Gamma": (Gamma, {"k": "k", "theta": "theta"}),
            "ChiSquared": (ChiSquared, {"k": "k"}),
            "Bernoulli": (Bernoulli, {"p": "p"}),
            "DiscreteUniform": (DiscreteUniform, {}),
        }

        entry = dist_info.get(distribution)
        if entry is None:
            return f"Unknown distribution '{distribution}'."
        dist_class, param_map = entry

        p = json.loads(params)
        mapped = {}
        for user_key, val in p.items():
            sympy_key = param_map.get(user_key, user_key)
            mapped[sympy_key] = val

        if distribution == "DiscreteUniform":
            items = mapped.get("items", list(range(1, int(mapped.get("max", 6)) + 1)))
            X = dist_class("X", items=items)
        else:
            X = dist_class("X", **mapped)

        if operation == "density":
            f = density(X)
            result = f

        elif operation == "expectation":
            result = E(X)

        elif operation == "variance":
            result = variance(X)

        elif operation == "std":
            result = std(X)

        elif operation == "probability":
            if not expression:
                return "Provide a condition expression (e.g. 'X > 3')."
            cond = sympify(expression, locals={"X": X})
            result = P(cond)

        elif operation == "cdf":
            f = cdf(X)
            if expression:
                result = f(sympify(expression))
            else:
                result = f

        elif operation == "sample":
            n = 5
            if expression:
                try:
                    n = int(expression)
                except ValueError:
                    pass
            n = max(1, min(n, 1000))
            try:
                samples = sample(X, size=n)
            except ImportError:
                return "Sampling requires scipy. Install with: pip install scipy"
            vals = [str(round(float(s), 6)) for s in samples]
            return f"[{', '.join(vals)}]"

        elif operation == "conditional":
            if not expression:
                return "Provide a condition expression (e.g. 'X > 0')."
            cond = sympify(expression, locals={"X": X})
            result = E(X, given(X, cond))

        else:
            return f"Unknown operation '{operation}'."

        return pretty(result)

    except Exception as e:
        return f"Statistics error: {e}"

TOOL_DISPATCH["stats_calc"] = stats_calc


# ---------------------------------------------------------------------------
# physics_constants
# ---------------------------------------------------------------------------

async def physics_constants(
    name: str,
    output_unit: str = "",
) -> str:
    try:
        from sympy.physics import units

        constant = getattr(units, name, None)
        if constant is None:
            available = [x for x in dir(units) if not x.startswith("_")]
            return (
                f"Unknown constant '{name}'.\n"
                f"Available constants include:\n"
                f"  speed_of_light, gravitational_constant, planck, hbar,\n"
                f"  boltzmann_constant, avogadro_constant, avogadro_number,\n"
                f"  electron_rest_mass, elementary_charge, vacuum_permittivity,\n"
                f"  vacuum_permeability, vacuum_impedance, stefan_boltzmann_constant,\n"
                f"  molar_gas_constant, faraday_constant, coulomb_constant,\n"
                f"  electronvolt, atomic_mass_unit, amu,\n"
                f"  planck_length, planck_time, planck_mass, planck_temperature,\n"
                f"  planck_charge, planck_energy, planck_force, planck_power,\n"
                f"  planck_pressure, planck_density, planck_current, planck_voltage,\n"
                f"  planck_impedance, planck_acceleration, planck_angular_frequency,\n"
                f"  planck_intensity, planck_energy_density, planck_momentum,\n"
                f"  planck_area, planck_volume"
            )

        from sympy.physics.units import convert_to
        from sympy.physics.units.systems.si import SI

        if output_unit:
            try:
                target_name = output_unit.lower().replace(" ", "_")
                target = getattr(units, target_name, None)
                if target is None and "/" in output_unit:
                    parts = output_unit.split("/")
                    num_name = parts[0].strip().lower()
                    den_name = parts[1].strip().lower()
                    num = getattr(units, num_name, None)
                    den = getattr(units, den_name, None)
                    if num and den:
                        target = num / den
                    else:
                        target = None
                if target is None:
                    target = sympify(output_unit)
                value = convert_to(constant, target)
                value = value.evalf()
            except Exception:
                value = constant
        else:
            try:
                factor = SI.get_quantity_scale_factor(constant)
                dimension = SI.get_quantity_dimension(constant)
                num_val = float(factor)
                dim_name = str(dimension).replace("Dimension(", "").replace(")", "")
                value = f"{num_val:.6e} [{dim_name}]"
            except Exception:
                value = constant

        name_str = name.replace("_", " ").title()
        val_str = str(value) if isinstance(value, str) else pretty(value)
        return f"{name_str} = {val_str}"

    except Exception as e:
        return f"Constants error: {e}"

TOOL_DISPATCH["physics_constants"] = physics_constants


# ---------------------------------------------------------------------------
# unit_converter
# ---------------------------------------------------------------------------

async def unit_converter(
    value: str,
    from_unit: str,
    to_unit: str,
) -> str:
    try:
        from sympy.physics import units
        from sympy.physics.units import convert_to

        val = sympify(value)

        src_name = from_unit.lower().replace(" ", "_")
        dst_name = to_unit.lower().replace(" ", "_")

        src = getattr(units, src_name, None)
        dst = getattr(units, dst_name, None)

        if src is None:
            return f"Unknown unit '{from_unit}'. Try: km, m, cm, mm, miles, yard, foot, inch, hour, minute, second, kg, g, lb, etc."
        if dst is None:
            return f"Unknown unit '{to_unit}'. Try: km, m, cm, mm, miles, yard, foot, inch, hour, minute, second, kg, g, lb, etc."

        try:
            converted = convert_to(val * src, dst)
        except Exception:
            dimension_src = getattr(src, "dimension", "?")
            dimension_dst = getattr(dst, "dimension", "?")
            return (
                f"Cannot convert: {from_unit} ({dimension_src}) "
                f"to {to_unit} ({dimension_dst}) — incompatible dimensions."
            )

        return pretty(converted)

    except Exception as e:
        return f"Conversion error: {e}"

TOOL_DISPATCH["unit_converter"] = unit_converter


# ---------------------------------------------------------------------------
# calculate
# ---------------------------------------------------------------------------

_CALC_SAFE_DICT = {
    "sin": __import__("math").sin,
    "cos": __import__("math").cos,
    "tan": __import__("math").tan,
    "asin": __import__("math").asin,
    "acos": __import__("math").acos,
    "atan": __import__("math").atan,
    "atan2": __import__("math").atan2,
    "sinh": __import__("math").sinh,
    "cosh": __import__("math").cosh,
    "tanh": __import__("math").tanh,
    "log": __import__("math").log,
    "log10": __import__("math").log10,
    "log2": __import__("math").log2,
    "exp": __import__("math").exp,
    "sqrt": __import__("math").sqrt,
    "abs": abs,
    "floor": __import__("math").floor,
    "ceil": __import__("math").ceil,
    "factorial": __import__("math").factorial,
    "degrees": __import__("math").degrees,
    "radians": __import__("math").radians,
    "pi": __import__("math").pi,
    "e": __import__("math").e,
    "tau": __import__("math").tau,
    "inf": float("inf"),
}


async def calculate(expression: str) -> str:
    try:
        result = eval(expression.strip(), {"__builtins__": {}}, _CALC_SAFE_DICT)
        return str(result)
    except Exception as e:
        return f"Error: {e}"

TOOL_DISPATCH["calculate"] = calculate


# ---------------------------------------------------------------------------
# run_python
# ---------------------------------------------------------------------------

_RUN_PYTHON_ALLOWED_MODULES = {
    "math", "itertools", "collections", "random", "statistics",
    "json", "re", "fractions", "decimal", "typing", "hashlib",
    "bisect", "heapq", "functools", "string", "time", "copy",
    "enum", "dataclasses", "pprint",
}

_RUN_PYTHON_SAFE_BUILTINS = {
    "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes",
    "chr", "complex", "dict", "dir", "divmod", "enumerate", "filter",
    "float", "format", "frozenset", "hash", "hex", "id", "int",
    "isinstance", "issubclass", "iter", "len", "list", "map", "max",
    "min", "next", "object", "oct", "ord", "pow", "print", "range",
    "repr", "reversed", "round", "set", "slice", "sorted", "str",
    "sum", "tuple", "type", "zip", "True", "False", "None",
    "Exception", "ValueError", "TypeError", "IndexError",
    "KeyError", "StopIteration", "RuntimeError", "ArithmeticError",
    "ZeroDivisionError", "OverflowError", "MemoryError",
}


def _run_python_sandbox(code: str, timeout: int = 30) -> str:
    import builtins
    import signal

    safe_builtins = {}
    for name in _RUN_PYTHON_SAFE_BUILTINS:
        if hasattr(builtins, name):
            safe_builtins[name] = getattr(builtins, name)

    def restricted_import(name, *args, **kwargs):
        if name not in _RUN_PYTHON_ALLOWED_MODULES:
            raise ImportError(
                f"Module '{name}' is not allowed. "
                f"Allowed modules: {', '.join(sorted(_RUN_PYTHON_ALLOWED_MODULES))}"
            )
        return __import__(name, *args, **kwargs)

    safe_builtins["__import__"] = restricted_import

    restricted_globals = {"__builtins__": safe_builtins}

    for mod_name in _RUN_PYTHON_ALLOWED_MODULES:
        try:
            restricted_globals[mod_name] = __import__(mod_name)
        except ImportError:
            pass

    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf

    class TimeoutError(Exception):
        pass

    def _timeout_handler(signum, frame):
        raise TimeoutError("Execution timed out (30 seconds)")

    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(timeout)

    try:
        exec(code, restricted_globals)
        signal.alarm(0)
        return buf.getvalue() or "(no output)"
    except TimeoutError as e:
        return str(e)
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
    finally:
        signal.alarm(0)
        sys.stdout = old_stdout
        signal.signal(signal.SIGALRM, old_handler)


async def run_python(code: str) -> str:
    return _run_python_sandbox(code)

TOOL_DISPATCH["run_python"] = run_python

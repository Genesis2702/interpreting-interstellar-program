from __future__ import annotations

from dataclasses import dataclass

from ifp_ast import TBinOp, TBool, TIf, TInt, TLam, TString, TUnOp, TVar, Term, CHARS_DECODED
from printer import encode_string, to_base94


MAX_STEPS = 10_000_000


class InterpreterError(Exception):
    pass


class BetaReductionLimit(InterpreterError):
    pass


class ScopeError(InterpreterError):
    pass


class TypeError_(InterpreterError):
    pass


class ArithmeticError_(InterpreterError):
    pass


class UnknownUnOp(InterpreterError):
    def __init__(self, op: str):
        super().__init__(f"Unknown unary operator: {op}")
        self.op = op


class UnknownBinOp(InterpreterError):
    def __init__(self, op: str):
        super().__init__(f"Unknown binary operator: {op}")
        self.op = op


@dataclass
class VInt:
    value: int


@dataclass
class VBool:
    value: bool


@dataclass
class VString:
    value: str


@dataclass
class VClosure:
    var: int
    body: Term
    env: dict[int, "Thunk"]


Value = VInt | VBool | VString | VClosure


@dataclass
class Thunk:
    kind: str
    value: Value | None = None
    steps: int = 0
    term: Term | None = None
    env: dict[int, "Thunk"] | None = None


def _to_term(v: Value) -> Term:
    if isinstance(v, VInt):
        return TInt(v.value)
    if isinstance(v, VBool):
        return TBool(v.value)
    if isinstance(v, VString):
        return TString(v.value)
    if isinstance(v, VClosure):
        return TLam(v.var, v.body)
    raise TypeError(f"Unknown value type: {type(v).__name__}")


def interpret(check_max: bool, term: Term) -> tuple[Term, int]:
    steps = 0

    def string_to_int(s: str) -> int:
        if not s:
            return 0
        val = 0
        for c in s:
            idx = CHARS_DECODED.find(c)
            if idx == -1:
                raise TypeError_()
            val = val * 94 + idx
        return val

    def int_to_string(num: int) -> str:
        if num < 0:
            raise ArithmeticError_()
        elif num == 0:
            return CHARS_DECODED[0]
        out: list[str] = []
        n = num
        while n > 0:
            n, m = divmod(n, 94)
            out.append(CHARS_DECODED[m])
        out.reverse()
        return "".join(out)

    def force_evaluation(thunk: Thunk) -> Value:
        if thunk.term is None or thunk.env is None:
            raise TypeError_()
        return eval_term(thunk.term, thunk.env)

    def eval_term(t: Term, env: dict[int, Thunk]) -> Value:
        nonlocal steps
        if isinstance(t, TBool):
            return VBool(t.value)
        elif isinstance(t, TInt):
            return VInt(t.value)
        elif isinstance(t, TString):
            return VString(t.value)
        elif isinstance(t, TVar):
            if t.value not in env:
                raise ScopeError()
            thunk = env[t.value]
            return force_evaluation(thunk)
        elif isinstance(t, TLam):
            return VClosure(t.var, t.body, env.copy())
        elif isinstance(t, TUnOp):
            op = t.op
            operand = eval_term(t.term, env)
            if op == "-":
                if not isinstance(operand, VInt):
                    raise TypeError_()
                return VInt(-operand.value)
            elif op == "!":
                if not isinstance(operand, VBool):
                    raise TypeError_()
                return VBool(not operand.value)
            elif op == "#":
                if not isinstance(operand, VString):
                    raise TypeError_()
                return VInt(string_to_int(operand.value))
            elif op == "$":
                if not isinstance(operand, VInt):
                    raise TypeError_()
                return VString(int_to_string(operand.value))
            else:
                raise UnknownUnOp(op)
        elif isinstance(t, TBinOp):
            op = t.op
            left = eval_term(t.left, env)
            if op == "$":
                if not isinstance(left, VClosure):
                    raise TypeError_()
                steps += 1
                if check_max and steps > MAX_STEPS:
                    raise BetaReductionLimit()
                new_env = left.env.copy()
                new_env[left.var] = Thunk(kind="thunk", term=t.right, env=env.copy())
                return eval_term(left.body, new_env)
            right = eval_term(t.right, env)
            if op in ("+", "-", "*", "/", "%"):
                if not isinstance(left, VInt) or not isinstance(right, VInt):
                    raise TypeError_()
                a = left.value
                b = right.value
                if op == "+":
                    return VInt(a + b)
                if op == "-":
                    return VInt(a - b)
                if op == "*":
                    return VInt(a * b)
                if op == "/":
                    if b == 0:
                        raise ArithmeticError_()
                    q = a // b if (a >= 0) == (b >= 0) else -((-a) // b)
                    return VInt(q)
                if op == "%":
                    if b == 0:
                        raise ArithmeticError_()
                    q = a // b if (a >= 0) == (b >= 0) else -((-a) // b)
                    return VInt(a - q * b)
            elif op in ("<", ">", "="):
                if op == "=":
                    if type(left) != type(right):
                        raise TypeError_()
                    if isinstance(left, (VInt, VBool, VString)):
                        return VBool(left.value == right.value)
                    raise TypeError_()
                elif op in ("<", ">"):
                    if not isinstance(left, VInt) or not isinstance(right, VInt):
                        raise TypeError_()
                    a = left.value
                    b = right.value
                    if op == "<":
                        return VBool(a < b)
                    if op == ">":
                        return VBool(a > b)
            elif op in ("|", "&"):
                if not isinstance(left, VBool) or not isinstance(right, VBool):
                    raise TypeError_()
                a = left.value
                b = right.value
                if op == "|":
                    return VBool(a or b)
                if op == "&":
                    return VBool(a and b)
            elif op == ".":
                if not isinstance(left, VString) or not isinstance(right, VString):
                    raise TypeError_()
                return VString(left.value + right.value)
            elif op == "T":
                if not isinstance(left, VInt) or not isinstance(right, VString):
                    raise TypeError_()
                x = max(0, left.value)
                return VString(right.value[:x])
            elif op == "D":
                if not isinstance(left, VInt) or not isinstance(right, VString):
                    raise TypeError_()
                x = max(0, left.value)
                return VString(right.value[x:])
            else:
                raise UnknownBinOp(op)
        elif isinstance(t, TIf):
            cond = eval_term(t.cond, env)
            if not isinstance(cond, VBool):
                raise TypeError_()
            branch = t.true_branch if cond.value else t.false_branch
            return eval_term(branch, env)

        raise TypeError(f"Unknown term type: {type(t).__name__}")

    result = eval_term(term, {})
    return _to_term(result), steps

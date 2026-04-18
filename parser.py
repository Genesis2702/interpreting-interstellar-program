from __future__ import annotations

from dataclasses import dataclass

from ifp_ast import (
    CHARS,
    CHARS_DECODED,
    TBinOp,
    TBool,
    TIf,
    TInt,
    TLam,
    TString,
    TUnOp,
    TVar,
    Term,
)


@dataclass(frozen=True)
class ParseError(Exception):
    kind: str
    index: int | None = None
    ch: str | None = None

    def __str__(self) -> str:
        if self.kind == "UnexpectedChar":
            return f"UnexpectedChar({self.ch!r}, {self.index})"
        if self.kind == "UnusedInput":
            return f"UnusedInput({self.index})"
        return "UnexpectedEOF"


def p_term(inp: str) -> Term:
    if not inp or not inp.strip():
        raise ParseError("UnexpectedEOF")

    tokens = inp.split()

    def base94_to_int(s: str) -> int:
        if not s:
            raise ParseError("UnexpectedEOF")
        val = 0
        for c in s:
            val = val * 94 + (ord(c) - 33)
        return val

    def decode_string(body: str) -> str:
        return "".join(CHARS_DECODED[ord(c) - 33] for c in body)

    def parse_next() -> Term:
        if not tokens:
            raise ParseError("UnexpectedEOF")
        token = tokens.pop(0)
        indicator = token[0]
        body = token[1:]
        if indicator == "T":
            return TBool(True)
        elif indicator == "F":
            return TBool(False)
        elif indicator == "I":
            if not body:
                raise ParseError("UnexpectedEOF")
            return TInt(base94_to_int(body))
        elif indicator == "S":
            if not body:
                raise ParseError("UnexpectedEOF")
            return TString(decode_string(body))
        elif indicator == "U":
            if not body:
                raise ParseError("UnexpectedEOF")
            return TUnOp(body, parse_next())
        elif indicator == "B":
            if not body:
                raise ParseError("UnexpectedEOF")
            left = parse_next()
            right = parse_next()
            return TBinOp(left, body, right)
        elif indicator == "?":
            condition = parse_next()
            true_branch = parse_next()
            false_branch = parse_next()
            return TIf(condition, true_branch, false_branch)
        elif indicator == "L":
            if not body:
                raise ParseError("UnexpectedEOF")
            variable = base94_to_int(body)
            term = parse_next()
            return TLam(variable, term)
        elif indicator == "v":
            if not body:
                raise ParseError("UnexpectedEOF")
            variable = base94_to_int(body)
            return TVar(variable)
        else:
            raise ParseError("UnexpectedChar", index=0, ch=indicator)

    term = parse_next()
    if tokens:
        raise ParseError("UnusedInput", index=0)
    return term
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
    if not inp:
        raise ParseError("UnexpectedEOF")

    n = len(inp)
    if inp[0] == ' ':
        raise ParseError("UnexpectedChar", index=0, ch=' ')

    for i in range(n - 1):
        if inp[i] == ' ' and inp[i + 1] == ' ':
            raise ParseError("UnexpectedChar", index=i + 1, ch=' ')

    if inp[-1] == ' ':
        clean = inp[:-1]
    else:
        clean = inp

    token_pairs = []
    if clean:
        pos = 0
        for token_str in clean.split(' '):
            token_pairs.append((token_str, pos))
            pos += len(token_str) + 1

    def base94_to_int(s: str) -> int:
        val = 0
        for c in s:
            val = val * 94 + (ord(c) - 33)
        return val

    def decode_string(body: str) -> str:
        return "".join(CHARS_DECODED[ord(c) - 33] for c in body)

    def parse_next() -> Term:
        if not token_pairs:
            raise ParseError("UnexpectedEOF", index=len(inp))
        token, idx = token_pairs.pop(0)
        indicator = token[0]
        body = token[1:]

        if indicator == "T":
            if body:
                raise ParseError("UnexpectedChar", index=idx + 1, ch=body[0])
            return TBool(True)
        elif indicator == "F":
            if body:
                raise ParseError("UnexpectedChar", index=idx + 1, ch=body[0])
            return TBool(False)
        elif indicator == "I":
            if not body:
                raise ParseError("UnexpectedEOF", index=idx + 1)
            return TInt(base94_to_int(body))
        elif indicator == "S":
            return TString(decode_string(body))
        elif indicator == "U":
            if not body:
                raise ParseError("UnexpectedEOF", index=idx + 1)
            return TUnOp(body, parse_next())
        elif indicator == "B":
            if not body:
                raise ParseError("UnexpectedEOF", index=idx + 1)
            left = parse_next()
            right = parse_next()
            return TBinOp(left, body, right)
        elif indicator == "?":
            if body:
                raise ParseError("UnexpectedChar", index=idx + 1, ch=body[0])
            condition = parse_next()
            true_branch = parse_next()
            false_branch = parse_next()
            return TIf(condition, true_branch, false_branch)
        elif indicator == "L":
            if not body:
                raise ParseError("UnexpectedEOF", index=idx + 1)
            variable = base94_to_int(body)
            term = parse_next()
            return TLam(variable, term)
        elif indicator == "v":
            if not body:
                raise ParseError("UnexpectedEOF", index=idx + 1)
            variable = base94_to_int(body)
            return TVar(variable)
        else:
            raise ParseError("UnexpectedChar", index=idx, ch=indicator)

    term = parse_next()
    if token_pairs:
        first_unused_idx = token_pairs[0][1]
        raise ParseError("UnusedInput", index=first_unused_idx)
    return term
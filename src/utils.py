from inspect import signature

def print_cols(row : list) -> None:
    i = 0
    for col in row:
        print(f'[{i}]\t{col} : {row[col]}')
        i += 1

def print_rows(fetchall: dict) -> None:
    for row in fetchall:
        print_cols(row)

def print_full_signature(function : callable) -> None:
    sig = signature(function)
    print(sig)
    print('  where')
    for param in sig.parameters:
        name = sig.parameters[param].name
        type = sig.parameters[param].annotation
        print(f'    {name} {type}')

def html_p(info : str) -> str:
    return f'<p>{info}</p>'

def html_h1(info : str) -> str:
    return f'<h1>{info}</h1>'
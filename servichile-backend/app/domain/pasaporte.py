import re
_RUT_PATRON = re.compile('^(\\d{1,8})-?([0-9K])$')

class RutInvalido(ValueError):
    pass

def dv_rut(cuerpo: str) -> str:
    suma = 0
    factor = 2
    for digito in reversed(cuerpo):
        suma += int(digito) * factor
        factor = factor + 1 if factor < 7 else 2
    resto = 11 - suma % 11
    if resto == 11:
        return '0'
    if resto == 10:
        return 'K'
    return str(resto)

def normalizar_rut(texto: str) -> str:
    limpio = texto.replace('.', '').replace(' ', '').upper()
    coincidencia = _RUT_PATRON.match(limpio)
    if not coincidencia:
        raise RutInvalido('Formato de RUT inválido.')
    cuerpo, dv = (coincidencia.group(1), coincidencia.group(2))
    if dv_rut(cuerpo) != dv:
        raise RutInvalido('El dígito verificador del RUT no es correcto.')
    return f'{cuerpo}-{dv}'

def score_confiabilidad(asistidos: int, no_show: int) -> float | None:
    cerradas = asistidos + no_show
    if cerradas == 0:
        return None
    return round(asistidos / cerradas * 100, 1)

def nivel_pasaporte() -> int:
    return 1

def estado_pasaporte(rut_verificado: bool) -> str:
    return 'verificado' if rut_verificado else 'basico'

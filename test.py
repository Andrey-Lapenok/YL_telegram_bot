def convert_to(number, base):
    digits = '0123456789abcdef'
    result = ''
    while number > 0:
        result = digits[number % base] + result
        number //= base
    return result

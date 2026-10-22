"""Line-by-line arithmetic from PHP Internal/Checksum.php."""


def luhn(digits: str) -> bool:
    total = 0
    double = False
    for i in range(len(digits) - 1, -1, -1):
        digit = int(digits[i])
        total += digit_sum(str(2 * digit)) if double else digit
        double = not double
    return total % 10 == 0


def iso7064_mod11_10(digits: str) -> bool:
    product = 10
    for i in range(len(digits) - 1):
        total = (int(digits[i]) + product) % 10
        product = 2 * (10 if total == 0 else total) % 11
    return (11 - product) % 10 == int(digits[-1:])


def iso7064_mod97_10(alphanumeric: str) -> bool:
    remainder = 0
    for character in alphanumeric:
        if character == "+":
            expanded = "36"
        elif character == "*":
            expanded = "37"
        else:
            expanded = character if "0" <= character <= "9" else str(ord(character) - 55)
        for digit in expanded:
            remainder = (remainder * 10 + int(digit)) % 97
    return remainder == 1


def weighted_sum(digits: str, weights: list[int]) -> int:
    total = 0
    for index, weight in enumerate(weights):
        total += int(digits[index]) * weight
    return total


def digit_sum(digits: str) -> int:
    total = 0
    for digit in digits:
        total += int(digit)
    return total

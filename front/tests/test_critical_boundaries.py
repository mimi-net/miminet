"""Критические границы входных значений перед сохранением сетевых заданий."""

import pytest

from miminet_host import (
    IPv4_check,
    MAC_check,
    data_size_check,
    interface_check,
    mask_check,
    name_check,
    port_check,
    time_check,
)


@pytest.mark.parametrize(
    "validator, minimum, maximum",
    [
        pytest.param(port_check, 0, 65535, id="port"),
        pytest.param(data_size_check, 0, 65535, id="data-size"),
        pytest.param(mask_check, 0, 32, id="mask"),
        pytest.param(time_check, 1, 50, id="time"),
    ],
)
@pytest.mark.parametrize("position", ["below", "minimum", "maximum", "above"])
def test_numeric_boundaries(validator, minimum, maximum, position):
    """Проверяем оба допустимых предела и соседние запрещённые значения.

    Нулевой порт здесь допустим согласно существующему контракту валидатора;
    это не означает, что он подходит для любой сетевой операции.
    """
    value, expected = {
        "below": (minimum - 1, False),
        "minimum": (minimum, True),
        "maximum": (maximum, True),
        "above": (maximum + 1, False),
    }[position]

    assert validator(str(value)) is expected


@pytest.mark.parametrize(
    "validator", [port_check, data_size_check, mask_check, time_check]
)
@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        " ",
        "1.5",
        "NaN",
        "1; reboot",
        pytest.param("9" * 5000, id="oversized-integer"),
    ],
)
def test_invalid_numeric_input_is_rejected_without_exception(validator, value):
    """Пустой, дробный, чрезмерно длинный или опасный ввод не вызывает падение."""
    assert validator(value) is False


@pytest.mark.parametrize(
    "address, expected",
    [
        ("0.0.0.0", True),
        ("255.255.255.255", True),
        ("256.0.0.1", False),
        ("192.168.1.-1", False),
        ("192.168.1", False),
        ("192.168.1.1/24", False),
        ("192.168.1.1; reboot", False),
        ("", False),
    ],
)
def test_ip_address_octet_boundaries_and_invalid_forms(address, expected):
    """Корректность записи адреса проверяется отдельно от его назначения в сети."""
    assert IPv4_check(address) is expected


@pytest.mark.parametrize(
    "validator, length, expected",
    [
        (name_check, 1, False),
        (name_check, 2, True),
        (name_check, 15, True),
        (name_check, 16, False),
        (interface_check, 1, True),
        (interface_check, 15, True),
        (interface_check, 16, False),
    ],
)
def test_name_length_boundaries(validator, length, expected):
    """Имена устройства и интерфейса имеют разные минимальные длины."""
    assert validator("a" * length) is expected


@pytest.mark.parametrize("validator", [name_check, interface_check])
@pytest.mark.parametrize("value", ["eth0;id", "eth0$(id)", "eth 0", "интерфейс"])
def test_names_reject_shell_syntax_spaces_and_non_ascii(validator, value):
    """Неподдерживаемые символы не должны попадать в сохранённые имена."""
    assert validator(value) is False


@pytest.mark.parametrize(
    "address, expected",
    [
        ("00:00:00:00:00:00", True),
        ("FF:FF:FF:FF:FF:FF", True),
        ("aa-bb-cc-dd-ee-ff", True),
        ("aabbccddeeff", True),
        ("aa:bb:cc:dd:ee", False),
        ("aa:bb:cc:dd:ee:ff:00", False),
        ("aa:bb-cc:dd:ee:ff", False),
        ("gg:bb:cc:dd:ee:ff", False),
    ],
)
def test_mac_address_length_and_separator_consistency(address, expected):
    """Проверяем формат MAC, включая крайние октеты и несовместимые разделители."""
    assert MAC_check(address) is expected


@pytest.mark.parametrize(
    "validator, value",
    [
        pytest.param(name_check, "router\n", id="device-name-newline"),
        pytest.param(MAC_check, "aa:bb:cc:dd:ee:ff\n", id="mac-newline"),
    ],
)
def test_trailing_newline_is_not_accepted_as_part_of_identifier(validator, value):
    """Полная строка обязана соответствовать формату, включая последний символ."""
    assert validator(value) is False

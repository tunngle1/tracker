"""
Pytest fixtures и конфигурация.
"""
import pytest


@pytest.fixture
def sample_date():
    """Образец даты для тестов."""
    from datetime import date
    return date(2024, 1, 15)

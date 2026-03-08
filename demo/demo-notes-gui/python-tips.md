# Python Best Practices

## Virtual Environments
Always use virtual environments:
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
```

## Code Style
- Follow PEP 8
- Use type hints
- Write docstrings

## Testing
Use pytest for testing:
```python
def test_example():
    assert add(2, 2) == 4
```

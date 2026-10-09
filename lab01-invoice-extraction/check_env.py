import sys
import anthropic
import dotenv

print("Intérprete:", sys.executable)
print("Python:", sys.version.split()[0])
print("SDK de Anthropic:", anthropic.__version__)
print("python-dotenv importado correctamente")
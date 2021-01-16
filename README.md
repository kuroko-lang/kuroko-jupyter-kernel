# Jupyter Kernel for Kuroko

This is a wrapper kernel for Jupyter that exectues Kuroko code.

Files in this repo:
 - `kurokokernel.py`: Kernel implementation. Binds library with `ctypes`, implements REPL semantics.
 - `kuroko/kernel.json`: Kernel spec for Jupyter.
 - `pygments/kuroko.py`: Pygments lexer for Kuroko.

## Installation

Install the kernel spec:

    jupyter  kernelspec install --user ./

Then put `kurokokernel.py` somewhere where Python can import it. Also make sure you have installed `libkuroko.so` and any modules you want to import appropriately.

If you want syntax highlighting, either install the Kuroko pygments lexer from `pygments/kuroko.py` (you need to rebuild the map files) or switch the kernel to use the `python` lexer instead, which is generally good enough.

## TODO

- Completion? We do this in our own REPL...
- Bindings for notebook functions? Image output?

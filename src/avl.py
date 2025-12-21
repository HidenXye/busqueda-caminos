from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Iterable, Optional, TypeVar

K = TypeVar("K")
V = TypeVar("V")


@dataclass
class _NodoAVL(Generic[K, V]):
    clave: K
    valores: list[V]
    altura: int = 1
    izq: Optional["_NodoAVL[K, V]"] = None
    der: Optional["_NodoAVL[K, V]"] = None


def _altura(nodo: Optional[_NodoAVL[K, V]]) -> int:
    return nodo.altura if nodo else 0


def _balance(nodo: Optional[_NodoAVL[K, V]]) -> int:
    if not nodo:
        return 0
    return _altura(nodo.izq) - _altura(nodo.der)


def _actualizar_altura(nodo: _NodoAVL[K, V]) -> None:
    nodo.altura = 1 + max(_altura(nodo.izq), _altura(nodo.der))


def _rotar_der(y: _NodoAVL[K, V]) -> _NodoAVL[K, V]:
    x = y.izq
    assert x is not None
    t2 = x.der

    x.der = y
    y.izq = t2

    _actualizar_altura(y)
    _actualizar_altura(x)
    return x


def _rotar_izq(x: _NodoAVL[K, V]) -> _NodoAVL[K, V]:
    y = x.der
    assert y is not None
    t2 = y.izq

    y.izq = x
    x.der = t2

    _actualizar_altura(x)
    _actualizar_altura(y)
    return y


class ArbolAVL(Generic[K, V]):
    """Árbol AVL simple, usado como estructura priorizada (orden por clave).

    Soporta claves duplicadas guardando una lista de valores por clave.
    """

    def __init__(self) -> None:
        self._raiz: Optional[_NodoAVL[K, V]] = None
        self._tam: int = 0

    def __len__(self) -> int:
        return self._tam

    def esta_vacio(self) -> bool:
        return self._tam == 0

    def insertar(self, clave: K, valor: V) -> None:
        self._raiz = self._insertar(self._raiz, clave, valor)
        self._tam += 1

    def extraer_minimo(self) -> tuple[K, V]:
        if not self._raiz:
            raise IndexError("El árbol AVL está vacío")
        clave, valor, nueva_raiz = self._extraer_minimo(self._raiz)
        self._raiz = nueva_raiz
        self._tam -= 1
        return clave, valor

    def _insertar(self, nodo: Optional[_NodoAVL[K, V]], clave: K, valor: V) -> _NodoAVL[K, V]:
        if nodo is None:
            return _NodoAVL(clave=clave, valores=[valor])

        if clave == nodo.clave:
            nodo.valores.append(valor)
            return nodo
        elif clave < nodo.clave:
            nodo.izq = self._insertar(nodo.izq, clave, valor)
        else:
            nodo.der = self._insertar(nodo.der, clave, valor)

        _actualizar_altura(nodo)
        bal = _balance(nodo)

        # Izq-Izq
        if bal > 1 and nodo.izq and clave < nodo.izq.clave:
            return _rotar_der(nodo)
        # Der-Der
        if bal < -1 and nodo.der and clave > nodo.der.clave:
            return _rotar_izq(nodo)
        # Izq-Der
        if bal > 1 and nodo.izq and clave > nodo.izq.clave:
            nodo.izq = _rotar_izq(nodo.izq)
            return _rotar_der(nodo)
        # Der-Izq
        if bal < -1 and nodo.der and clave < nodo.der.clave:
            nodo.der = _rotar_der(nodo.der)
            return _rotar_izq(nodo)

        return nodo

    def _extraer_minimo(self, nodo: _NodoAVL[K, V]) -> tuple[K, V, Optional[_NodoAVL[K, V]]]:
        if nodo.izq is None:
            # Este nodo tiene la clave mínima
            valor = nodo.valores.pop()
            if nodo.valores:
                return nodo.clave, valor, nodo
            return nodo.clave, valor, nodo.der

        clave, valor, nueva_izq = self._extraer_minimo(nodo.izq)
        nodo.izq = nueva_izq

        _actualizar_altura(nodo)
        bal = _balance(nodo)

        # Rebalanceo
        if bal > 1:
            assert nodo.izq is not None
            if _balance(nodo.izq) >= 0:
                return clave, valor, _rotar_der(nodo)
            nodo.izq = _rotar_izq(nodo.izq)
            return clave, valor, _rotar_der(nodo)

        if bal < -1:
            assert nodo.der is not None
            if _balance(nodo.der) <= 0:
                return clave, valor, _rotar_izq(nodo)
            nodo.der = _rotar_der(nodo.der)
            return clave, valor, _rotar_izq(nodo)

        return clave, valor, nodo

    def items_ordenados(self) -> Iterable[tuple[K, V]]:
        yield from self._inorder(self._raiz)

    def _inorder(self, nodo: Optional[_NodoAVL[K, V]]):
        if nodo is None:
            return
        yield from self._inorder(nodo.izq)
        for v in nodo.valores:
            yield nodo.clave, v
        yield from self._inorder(nodo.der)

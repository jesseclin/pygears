from .base import EnumerableGenericMeta
from .unit import Unit


class ArrayMeta(EnumerableGenericMeta):
    def keys(self):
        """Returns a list of keys that can be used for indexing :class:`Array` [T, N] type. Number of keys equals to the number of elements N.

        >>> assert Array[Uint[2], 5].keys() == [0, 1, 2, 3, 4]
        """

        return list(range(int(self.args[1])))

    def __new__(cls, name, bases, namespace, args=[]):
        cls = super().__new__(cls, name, bases, namespace, args)

        if len(cls.args) < 2:
            # Generic parameter values have not been supplied
            return cls
        else:
            # If Array of Units, return Unit
            if cls.args[0] == Unit:
                return Unit

            if cls.args[1] == 1:
                # If Array of length 1, return original type
                return cls.args[0]
            elif cls.args[1] == 0:
                # If Array of length 0, return Unit
                return Unit

            # Otherwise, return the Array class
            return cls

    def __getitem__(self, index):
        """If a single element is supplied for index, returns type T. If a slice is suplied for index, an :class:`Array` type is returned with a number of elements equal to the slice size.

        >>> assert Array[Uint[2], 5][3] == Uint[2]
        >>> assert Array[Uint[2], 5][2:4] == Array[Uint[2], 2]
        """

        if not self.is_specified():
            return super().__getitem__(index)

        index = self.index_norm(index)

        width = 0
        for i in index:
            if isinstance(i, slice):
                if (i.stop == 0) or (i.stop - i.start > len(self)):
                    raise IndexError
                width += i.stop - i.start
            else:
                if i >= len(self):
                    raise IndexError
                width += 1

        return Array[self.args[0], width]

    def __str__(self):
        return f'Array[{str(self.args[0])}, {len(self)}]'


class Array(metaclass=ArrayMeta):
    """Generic container datatype that holds N instances of type T

    Generic parameters:
       T: Type of the :class:`Array` [T, N] elements

       N: Number of elements in the :class:`Array` [T, N]

    Concrete data type is obtained by indexing:

    >>> u16_4 = Array[Uint[16], 4]

    """
    __parameters__ = ['T', 'N']
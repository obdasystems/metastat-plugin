# -*- coding: utf-8 -*-

##########################################################################
#                                                                        #
#  Eddy: a graphical editor for the specification of Graphol ontologies  #
#  Copyright (C) 2015 Daniele Pantaleone <danielepantaleone@me.com>      #
#                                                                        #
#  This program is free software: you can redistribute it and/or modify  #
#  it under the terms of the GNU General Public License as published by  #
#  the Free Software Foundation, either version 3 of the License, or     #
#  (at your option) any later version.                                   #
#                                                                        #
#  This program is distributed in the hope that it will be useful,       #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of        #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the          #
#  GNU General Public License for more details.                          #
#                                                                        #
#  You should have received a copy of the GNU General Public License     #
#  along with this program. If not, see <http://www.gnu.org/licenses/>.  #
#                                                                        #
#  #####################                          #####################  #
#                                                                        #
#  Graphol is developed by members of the DASI-lab group of the          #
#  Dipartimento di Ingegneria Informatica, Automatica e Gestionale       #
#  A.Ruberti at Sapienza University of Rome: http://www.dis.uniroma1.it  #
#                                                                        #
#     - Domenico Lembo <lembo@dis.uniroma1.it>                           #
#     - Valerio Santarelli <santarelli@dis.uniroma1.it>                  #
#     - Domenico Fabio Savo <savo@dis.uniroma1.it>                       #
#     - Daniele Pantaleone <pantaleone@dis.uniroma1.it>                  #
#     - Marco Console <console@dis.uniroma1.it>                          #
#                                                                        #
##########################################################################


from __future__ import annotations

from abc import (
    ABCMeta,
    abstractmethod,
)


class Node(metaclass=ABCMeta):
    """
    Base class for any API object.
    """

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict, **kwargs: dict):
        """Creates a new node from the given dict."""
        pass

    @abstractmethod
    def to_dict(self, deep: bool = False) -> dict:
        """Serializes the object to a dict."""
        pass


class LiteralValue(Node):
    """
    Represent a literal value associated with entity metadata.
    """

    def __init__(self, value: str, language: str | None = None) -> None:
        """Initialize the literal."""
        super().__init__()
        self._value = value
        self._lang = language

    @property
    def value(self) -> str:
        """Return the value of this literal."""
        return self._value

    @property
    def lang(self) -> str | None:
        """Return the language tag of this literal, or `None` if there is no tag."""
        return self._lang

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> LiteralValue:
        return cls(data["value"], data["lang"])

    def to_dict(self, deep: bool = False) -> dict:
        return {
            "value": self.value,
            "lang": self.lang,
        }

    def __eq__(self, other: LiteralValue) -> bool:
        return (
                super().__eq__(other)
                and self.value == other.value
                and self.lang == other.lang
        )

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}("{self.value}"@{self.lang})'


class Owner(Node):
    """
    Represents process owners.
    """

    def __init__(self, id_: str, name: str) -> None:
        """Initialize the named entity."""
        super().__init__()
        self._id = id_
        self._name = name

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> Owner:
        return Owner(data.get("id"), data.get("name"))

    def to_dict(self, deep: bool = False) -> dict:
        res = {}
        if self.id:
            res['id'] = self.id
        if self.name:
            res['name'] = self.name
        return res


class NamedEntity(Node):
    """
    Represents entities that are uniquely identified with an IRI.
    """

    def __init__(self, id_: str) -> None:
        """Initialize the named entity."""
        super().__init__()
        self._id = id_
        self._type = None
        self._lemmas = []
        self._definitions = []
        self._owner = None

    @property
    def id(self) -> str:
        """Return the id of the entity."""
        return self._id

    @property
    def iri(self):
        """Return the IRI associated with the entity."""
        return f"http://www.istat.it/metastat/{self.id}"

    @property
    def type(self) -> str:
        """Return the type of this entity."""
        return self._type

    @property
    def lemma(self) -> list[LiteralValue]:
        """Return the list of lemmas for this entity."""
        return self._lemmas

    @property
    def definition(self) -> list[LiteralValue]:
        """Return the list of definitions for this entity."""
        return self._definitions

    @property
    def owner(self) -> Owner:
        """Return the process owner for this entity."""
        return self._owner

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> NamedEntity:
        entity = NamedEntity(data["id"])
        entity._type = data["type"]
        if "lemma" in data:
            entity._lemmas.extend([LiteralValue.from_dict(l) for l in data["lemma"]])
        if "definition" in data:
            entity._definitions.extend([LiteralValue.from_dict(d) for d in data["definition"]])
        if "owner" in data:
            entity._owner = Owner.from_dict(data["owner"])
        return entity

    def to_dict(self, deep: bool = False) -> dict:
        res = {
            "id": self.id,
            "type": self.type,
        }
        if deep:
            res |= {
                "lemma": [a.to_dict() for a in self.lemma],
                "definition": [a.to_dict() for a in self.definition],
                "owner": self.owner.to_dict() if self.owner else {},
            }
        return res

    def __eq__(self, other) -> bool:
        return super().__eq__(other) and self.id == other.id

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.id}, \"{self.type}\")"

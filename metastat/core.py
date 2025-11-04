from abc import ABCMeta, abstractmethod
from typing import cast, Optional, Union

from rdflib import (
    BNode,
    Graph,
    IdentifiedNode,
    Literal,
    URIRef,
)

K_GRAPH = Graph(bind_namespaces='none')


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
    def from_dict(cls, data: dict, **kwargs) -> Node:
        if "id" in data:
            owner = Owner(data["id"], data["name"])
            return owner
        return None

    def to_dict(self, deep: bool = False) -> dict:
        res = {
            "id": self.id,
            "name": self.name,
        }
        return res

class NamedEntity(Node):
    """
    Represents entities that are uniquely identified with an IRI.
    """

    def __init__(self, id_: str ) -> None:
        """Initialize the named entity."""
        super().__init__()
        self._id = id_
        self._iri = id_ if isinstance(id_, URIRef) else URIRef(id_)
        self.lemmas = []
        self.definitions = []
        self.type = None
        self.owner = None

    @property
    def iri(self) -> URIRef:
        """Return the iri associated with this named entity."""
        return self._iri

    @property
    def id(self) -> IdentifiedNode:
        return self._id

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> Node:
        ent = NamedEntity(data["id"])  # noqa
        ent.type = data["type"]
        if "owner" in data:
            ownerData = data["owner"]
            owner = cast(Owner, Owner.from_dict(data=ownerData))
            ent.owner = owner
        if "lemma" in data:
            lemma_pred_dict = {"iri": "http://www.w3.org/2000/01/rdf-schema#label"}
            for a in data["lemma"]:
                ant = cast(Annotation, Annotation.from_dict(a, subject=ent.to_dict(), predicate=lemma_pred_dict))
                ent.lemmas.append(ant)
        if "definition" in data:
            definition_pred_dict = {"iri": "http://www.w3.org/2000/01/rdf-schema#comment"}
            for a in data["definition"]:
                ant = cast(Annotation, Annotation.from_dict(a, subject=ent.to_dict(), predicate=definition_pred_dict))
                ent.definitions.append(ant)
        return ent

    def to_dict(self, deep: bool = False) -> dict:
        res = {
            "id": self.id,
            "type": self.type,
        }
        if deep:
            res |= {
                "lemma": [a.to_dict() for a in self.lemmas],
                "definition": [a.to_dict() for a in self.definitions],
                "owner": self.owner.to_dict(),
            }
        return res

    def n3(self) -> str:
        return self.iri.n3(K_GRAPH.namespace_manager)

    def __eq__(self, other: Node) -> bool:
        return super().__eq__(other) and self.id == cast(NamedEntity, other).id

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.id}, \"{self.type}\")"

class Annotation(Node):
    """
    Represent an annotation assertion.
    """

    def __init__(self, subject: NamedEntity, predicate: URIRef, object: Node) -> None:
        """Initialize the annotation."""
        self._subject = subject
        self._predicate = predicate
        self._object = object

    @property
    def subject(self) -> NamedEntity:
        """Return the annotation subject."""
        return self._subject

    @property
    def predicate(self) -> URIRef:
        """Return the annotation predicate."""
        return self._predicate

    @property
    def object(self) -> Node:
        """Return the annotation object."""
        return self._object

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> Node:
        s = kwargs["subject"]
        p = kwargs["predicate"]["iri"]
        v = data["value"]
        l = data["lang"]

        sub = NamedEntity.from_dict(s)
        prop = URIRef(p)

        if isinstance(v, dict) and "id" in v:
            obj = NamedEntity.from_dict(v) if "iri" in v else AnonymousEntity.from_dict(v)
        else:
            obj = LiteralValue.from_dict({"value": v, "language": l})
        return Annotation(cast(NamedEntity, sub), prop, obj)

    def to_dict(self, deep: bool = False) -> dict:
        return {
            "property": self.predicate,
            "value": self.object.to_dict()
        }

    def n3(self) -> str:
        sub = self.subject.n3()
        pred = self.predicate.n3()
        obj = self.object.n3()
        return f'{sub} {pred} {obj}'

    def __eq__(self, other: Node) -> bool:
        return (
            self.__class__ == other.__class__
            and self.subject == cast(Annotation, other).subject
            and self.predicate == cast(Annotation, other).predicate
            and self.object == cast(Annotation, other).object
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.subject}, {self.predicate}, {self.object})"


class LiteralValue(Node):
    """
    Represent a literal value associated with an annotation assertion.
    """

    def __init__(self, value: str, language: Optional[str] = None,
                 ) -> None:
        """Initialize the literal."""
        super().__init__()
        self._value = value
        self._language = language
        self._datatype = None
        # Check that literal is well-formed
        if self._language is not None and self._datatype is not None:
            raise ValueError("Literals with a datatype cannot have a language tag.")

    @property
    def value(self) -> str:
        """Return the value of this literal."""
        return self._value

    @property
    def language(self) -> Optional[str]:
        """Return the language tag of this literal, or `None` if there is no tag."""
        return self._language

    @property
    def datatype(self) -> Optional[Union[URIRef, str]]:
        """Return the datatype of this literal, or `None` if there is no datatype."""
        return self._datatype

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> Node:
        return cls(data["value"], data["language"])  # noqa

    def to_dict(self, deep: bool = False) -> dict:
        return {
            "value": self.value,
            "language": self.language,
        }

    def n3(self) -> str:
        return Literal(self.value, self.language, self.datatype).n3(K_GRAPH.namespace_manager)

    def __eq__(self, other: Node) -> bool:
        return (
            super().__eq__(other)
            and self.value == cast(LiteralValue, other).value
            and self.language == cast(LiteralValue, other).language
        )

    def __repr__(self) -> str:
        if self.language:
            return f"{self.__class__.__name__}(\"{self.value}\"@{self.language})"
        else:
            return f"{self.__class__.__name__}(\"{self.value}\"^^{self.datatype})"

class AnonymousEntity(Node):
    """
    Represents entities not identified by an IRI (i.e. blank nodes in RDF).
    """

    def __init__(self, id_: str, bnode: Union[BNode, str]) -> None:
        """Initialize the anonymous entity."""
        super().__init__()
        self._id = id_
        self._bnode = bnode if isinstance(bnode, BNode) else BNode(bnode)

    @property
    def bnode(self) -> BNode:
        """Returns the blank node associated with this entity."""
        return self._bnode

    @property
    def name(self) -> IdentifiedNode:
        return self.bnode

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> Node:
        ent = NamedEntity(data["id"], data["bnode"])  # noqa
        ent = NamedEntity(data["id"])  # noqa
        ent.type = data["type"]
        owner = cast(Owner, Owner.from_dict(data))
        ent.owner = owner
        if "lemma" in data:
            lemma_pred_dict = {"iri": "http://www.w3.org/2000/01/rdf-schema#label"}
            for a in data["lemma"]:
                ant = cast(Annotation, Annotation.from_dict(a, subject=ent.to_dict(), predicate=lemma_pred_dict))
                ent.lemmas.append(ant)
        if "definition" in data:
            definition_pred_dict = {"iri": "http://www.w3.org/2000/01/rdf-schema#comment"}
            for a in data["definition"]:
                ant = cast(Annotation, Annotation.from_dict(a, subject=ent.to_dict(), predicate=definition_pred_dict))
                ent.definitions.append(ant)
        return ent

    def to_dict(self, deep: bool = False) -> dict:
        res = {
            "id": self.id,
            "type": self.type,
        }
        if deep:
            res |= {
                "lemma": [a.to_dict() for a in self.lemmas],
                "definition": [a.to_dict() for a in self.definitions],
                "owner": self.owner.to_dict(),
            }
        return res

    def n3(self) -> str:
        return self.bnode.n3(K_GRAPH.namespace_manager)

    def __eq__(self, other: Node) -> bool:
        return super().__eq__(other) and self.bnode == cast(AnonymousEntity, other).bnode

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.id}, \"{self.bnode}\")"

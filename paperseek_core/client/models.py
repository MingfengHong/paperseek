# pydantic models for WoS Starter API responses
from __future__ import annotations
import pprint, re, json
from typing import Any, ClassVar, Dict, List, Optional
from pydantic import BaseModel, StrictStr, StrictInt, field_validator
from pydantic import Field
try: from typing import Self
except ImportError: from typing_extensions import Self

class AuthorName(BaseModel):
    """
    AuthorName
    """ # noqa: E501
    display_name: Optional[StrictStr] = Field(default=None, description="Web of Science display name", alias="displayName")
    wos_standard: Optional[StrictStr] = Field(default=None, description="Web of Science standard name", alias="wosStandard")
    researcher_id: Optional[StrictStr] = Field(default=None, description="Web of Science ResearcherID", alias="researcherId")
    __properties: ClassVar[List[str]] = ["displayName", "wosStandard", "researcherId"]

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
    }


    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        return self.model_dump_json(by_alias=True, exclude_unset=True)

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Create an instance of AuthorName from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        _dict = self.model_dump(
            by_alias=True,
            exclude={
            },
            exclude_none=True,
        )
        return _dict

    @classmethod
    def from_dict(cls, obj: Dict) -> Self:
        """Create an instance of AuthorName from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "displayName": obj.get("displayName"),
            "wosStandard": obj.get("wosStandard"),
            "researcherId": obj.get("researcherId")
        })
        return _obj




class DocumentCitationsInner(BaseModel):
    """
    DocumentCitationsInner
    """ # noqa: E501
    db: Optional[StrictStr] = Field(default=None, description="Web of Science Citation Database (collection) Abbreviation Name")
    count: Optional[StrictInt] = Field(default=None, description="Citation Count")
    __properties: ClassVar[List[str]] = ["db", "count"]

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
    }


    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        # TODO: pydantic v2: use .model_dump_json(by_alias=True, exclude_unset=True) instead
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Create an instance of DocumentCitationsInner from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        _dict = self.model_dump(
            by_alias=True,
            exclude={
            },
            exclude_none=True,
        )
        return _dict

    @classmethod
    def from_dict(cls, obj: Dict) -> Self:
        """Create an instance of DocumentCitationsInner from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "db": obj.get("db"),
            "count": obj.get("count")
        })
        return _obj




class DocumentIdentifiers(BaseModel):
    """
    Document and Source Identifiers
    """ # noqa: E501
    doi: Optional[StrictStr] = None
    issn: Optional[StrictStr] = None
    eissn: Optional[StrictStr] = None
    isbn: Optional[StrictStr] = None
    eisbn: Optional[StrictStr] = None
    pmid: Optional[StrictStr] = None
    __properties: ClassVar[List[str]] = ["doi", "issn", "eissn", "isbn", "eisbn", "pmid"]

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
    }


    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        # TODO: pydantic v2: use .model_dump_json(by_alias=True, exclude_unset=True) instead
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Create an instance of DocumentIdentifiers from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        _dict = self.model_dump(
            by_alias=True,
            exclude={
            },
            exclude_none=True,
        )
        return _dict

    @classmethod
    def from_dict(cls, obj: Dict) -> Self:
        """Create an instance of DocumentIdentifiers from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "doi": obj.get("doi"),
            "issn": obj.get("issn"),
            "eissn": obj.get("eissn"),
            "isbn": obj.get("isbn"),
            "eisbn": obj.get("eisbn"),
            "pmid": obj.get("pmid")
        })
        return _obj




class DocumentKeywords(BaseModel):
    """
    Author keywords
    """ # noqa: E501
    author_keywords: Optional[List[StrictStr]] = Field(default=None, alias="authorKeywords")
    __properties: ClassVar[List[str]] = ["authorKeywords"]

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
    }


    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        # TODO: pydantic v2: use .model_dump_json(by_alias=True, exclude_unset=True) instead
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Create an instance of DocumentKeywords from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        _dict = self.model_dump(
            by_alias=True,
            exclude={
            },
            exclude_none=True,
        )
        return _dict

    @classmethod
    def from_dict(cls, obj: Dict) -> Self:
        """Create an instance of DocumentKeywords from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "authorKeywords": obj.get("authorKeywords")
        })
        return _obj




class DocumentLinks(BaseModel):
    """
    Web of Science URLs
    """ # noqa: E501
    record: Optional[StrictStr] = None
    citing_articles: Optional[StrictStr] = Field(default=None, alias="citingArticles")
    references: Optional[StrictStr] = None
    related: Optional[StrictStr] = None
    __properties: ClassVar[List[str]] = ["record", "citingArticles", "references", "related"]

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
    }


    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        # TODO: pydantic v2: use .model_dump_json(by_alias=True, exclude_unset=True) instead
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Create an instance of DocumentLinks from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        _dict = self.model_dump(
            by_alias=True,
            exclude={
            },
            exclude_none=True,
        )
        return _dict

    @classmethod
    def from_dict(cls, obj: Dict) -> Self:
        """Create an instance of DocumentLinks from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "record": obj.get("record"),
            "citingArticles": obj.get("citingArticles"),
            "references": obj.get("references"),
            "related": obj.get("related")
        })
        return _obj




class DocumentNames(BaseModel):
    """
    DocumentNames
    """ # noqa: E501
    authors: Optional[List[AuthorName]] = Field(default=None, description="Authors of document")
    inventors: Optional[List[OtherName]] = None
    book_corp: Optional[List[OtherName]] = Field(default=None, alias="bookCorp")
    book_editors: Optional[List[OtherName]] = Field(default=None, alias="bookEditors")
    books: Optional[List[OtherName]] = None
    additional_authors: Optional[List[OtherName]] = Field(default=None, alias="additionalAuthors")
    anonymous: Optional[List[OtherName]] = None
    assignees: Optional[List[OtherName]] = None
    corp: Optional[List[OtherName]] = None
    editors: Optional[List[OtherName]] = None
    investigators: Optional[List[OtherName]] = None
    sponsors: Optional[List[OtherName]] = None
    issuing_organizations: Optional[List[OtherName]] = Field(default=None, alias="issuingOrganizations")
    __properties: ClassVar[List[str]] = ["authors", "inventors", "bookCorp", "bookEditors", "books", "additionalAuthors", "anonymous", "assignees", "corp", "editors", "investigators", "sponsors", "issuingOrganizations"]

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
    }


    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        # TODO: pydantic v2: use .model_dump_json(by_alias=True, exclude_unset=True) instead
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Create an instance of DocumentNames from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        _dict = self.model_dump(
            by_alias=True,
            exclude={
            },
            exclude_none=True,
        )
        # override the default output from pydantic by calling `to_dict()` of each item in authors (list)
        _items = []
        if self.authors:
            for _item in self.authors:
                if _item:
                    _items.append(_item.to_dict())
            _dict['authors'] = _items
        # override the default output from pydantic by calling `to_dict()` of each item in inventors (list)
        _items = []
        if self.inventors:
            for _item in self.inventors:
                if _item:
                    _items.append(_item.to_dict())
            _dict['inventors'] = _items
        # override the default output from pydantic by calling `to_dict()` of each item in book_corp (list)
        _items = []
        if self.book_corp:
            for _item in self.book_corp:
                if _item:
                    _items.append(_item.to_dict())
            _dict['bookCorp'] = _items
        # override the default output from pydantic by calling `to_dict()` of each item in book_editors (list)
        _items = []
        if self.book_editors:
            for _item in self.book_editors:
                if _item:
                    _items.append(_item.to_dict())
            _dict['bookEditors'] = _items
        # override the default output from pydantic by calling `to_dict()` of each item in books (list)
        _items = []
        if self.books:
            for _item in self.books:
                if _item:
                    _items.append(_item.to_dict())
            _dict['books'] = _items
        # override the default output from pydantic by calling `to_dict()` of each item in additional_authors (list)
        _items = []
        if self.additional_authors:
            for _item in self.additional_authors:
                if _item:
                    _items.append(_item.to_dict())
            _dict['additionalAuthors'] = _items
        # override the default output from pydantic by calling `to_dict()` of each item in anonymous (list)
        _items = []
        if self.anonymous:
            for _item in self.anonymous:
                if _item:
                    _items.append(_item.to_dict())
            _dict['anonymous'] = _items
        # override the default output from pydantic by calling `to_dict()` of each item in assignees (list)
        _items = []
        if self.assignees:
            for _item in self.assignees:
                if _item:
                    _items.append(_item.to_dict())
            _dict['assignees'] = _items
        # override the default output from pydantic by calling `to_dict()` of each item in corp (list)
        _items = []
        if self.corp:
            for _item in self.corp:
                if _item:
                    _items.append(_item.to_dict())
            _dict['corp'] = _items
        # override the default output from pydantic by calling `to_dict()` of each item in editors (list)
        _items = []
        if self.editors:
            for _item in self.editors:
                if _item:
                    _items.append(_item.to_dict())
            _dict['editors'] = _items
        # override the default output from pydantic by calling `to_dict()` of each item in investigators (list)
        _items = []
        if self.investigators:
            for _item in self.investigators:
                if _item:
                    _items.append(_item.to_dict())
            _dict['investigators'] = _items
        # override the default output from pydantic by calling `to_dict()` of each item in sponsors (list)
        _items = []
        if self.sponsors:
            for _item in self.sponsors:
                if _item:
                    _items.append(_item.to_dict())
            _dict['sponsors'] = _items
        # override the default output from pydantic by calling `to_dict()` of each item in issuing_organizations (list)
        _items = []
        if self.issuing_organizations:
            for _item in self.issuing_organizations:
                if _item:
                    _items.append(_item.to_dict())
            _dict['issuingOrganizations'] = _items
        return _dict

    @classmethod
    def from_dict(cls, obj: Dict) -> Self:
        """Create an instance of DocumentNames from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "authors": [AuthorName.from_dict(_item) for _item in obj.get("authors")] if obj.get("authors") is not None else None,
            "inventors": [OtherName.from_dict(_item) for _item in obj.get("inventors")] if obj.get("inventors") is not None else None,
            "bookCorp": [OtherName.from_dict(_item) for _item in obj.get("bookCorp")] if obj.get("bookCorp") is not None else None,
            "bookEditors": [OtherName.from_dict(_item) for _item in obj.get("bookEditors")] if obj.get("bookEditors") is not None else None,
            "books": [OtherName.from_dict(_item) for _item in obj.get("books")] if obj.get("books") is not None else None,
            "additionalAuthors": [OtherName.from_dict(_item) for _item in obj.get("additionalAuthors")] if obj.get("additionalAuthors") is not None else None,
            "anonymous": [OtherName.from_dict(_item) for _item in obj.get("anonymous")] if obj.get("anonymous") is not None else None,
            "assignees": [OtherName.from_dict(_item) for _item in obj.get("assignees")] if obj.get("assignees") is not None else None,
            "corp": [OtherName.from_dict(_item) for _item in obj.get("corp")] if obj.get("corp") is not None else None,
            "editors": [OtherName.from_dict(_item) for _item in obj.get("editors")] if obj.get("editors") is not None else None,
            "investigators": [OtherName.from_dict(_item) for _item in obj.get("investigators")] if obj.get("investigators") is not None else None,
            "sponsors": [OtherName.from_dict(_item) for _item in obj.get("sponsors")] if obj.get("sponsors") is not None else None,
            "issuingOrganizations": [OtherName.from_dict(_item) for _item in obj.get("issuingOrganizations")] if obj.get("issuingOrganizations") is not None else None
        })
        return _obj




class DocumentSourcePages(BaseModel):
    """
    DocumentSourcePages
    """ # noqa: E501
    range: Optional[StrictStr] = Field(default=None, description="Page range")
    begin: Optional[StrictStr] = Field(default=None, description="Page begin")
    end: Optional[StrictStr] = Field(default=None, description="Page end")
    count: Optional[StrictInt] = Field(default=None, description="Number of pages")
    __properties: ClassVar[List[str]] = ["range", "begin", "end", "count"]

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
    }


    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        # TODO: pydantic v2: use .model_dump_json(by_alias=True, exclude_unset=True) instead
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Create an instance of DocumentSourcePages from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        _dict = self.model_dump(
            by_alias=True,
            exclude={
            },
            exclude_none=True,
        )
        return _dict

    @classmethod
    def from_dict(cls, obj: Dict) -> Self:
        """Create an instance of DocumentSourcePages from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "range": obj.get("range"),
            "begin": obj.get("begin"),
            "end": obj.get("end"),
            "count": obj.get("count")
        })
        return _obj




class DocumentSource(BaseModel):
    """
    Web of Science document source metadata
    """ # noqa: E501
    source_title: Optional[StrictStr] = Field(default=None, description="Source title", alias="sourceTitle")
    publish_year: Optional[StrictInt] = Field(default=None, description="Published Year", alias="publishYear")
    publish_month: Optional[StrictStr] = Field(default=None, description="Published Month", alias="publishMonth")
    volume: Optional[StrictStr] = Field(default=None, description="Volume")
    issue: Optional[StrictStr] = Field(default=None, description="Issue")
    supplement: Optional[StrictStr] = Field(default=None, description="Journal supplement")
    special_issue: Optional[StrictStr] = Field(default=None, description="Journal special issue", alias="specialIssue")
    article_number: Optional[StrictStr] = Field(default=None, description="Source Article Number", alias="articleNumber")
    pages: Optional[DocumentSourcePages] = None
    __properties: ClassVar[List[str]] = ["sourceTitle", "publishYear", "publishMonth", "volume", "issue", "supplement", "specialIssue", "articleNumber", "pages"]

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
    }


    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        # TODO: pydantic v2: use .model_dump_json(by_alias=True, exclude_unset=True) instead
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Create an instance of DocumentSource from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        _dict = self.model_dump(
            by_alias=True,
            exclude={
            },
            exclude_none=True,
        )
        # override the default output from pydantic by calling `to_dict()` of pages
        if self.pages:
            _dict['pages'] = self.pages.to_dict()
        return _dict

    @classmethod
    def from_dict(cls, obj: Dict) -> Self:
        """Create an instance of DocumentSource from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "sourceTitle": obj.get("sourceTitle"),
            "publishYear": obj.get("publishYear"),
            "publishMonth": obj.get("publishMonth"),
            "volume": obj.get("volume"),
            "issue": obj.get("issue"),
            "supplement": obj.get("supplement"),
            "specialIssue": obj.get("specialIssue"),
            "articleNumber": obj.get("articleNumber"),
            "pages": DocumentSourcePages.from_dict(obj.get("pages")) if obj.get("pages") is not None else None
        })
        return _obj




class Metadata(BaseModel):
    """
    Information about total number of journals in the retrieve, number of recodrs on the page, and the page number
    """ # noqa: E501
    page: Optional[StrictInt] = Field(default=None, description="Page number (default is 1)")
    limit: Optional[StrictInt] = Field(default=None, description="Number of records on a page (default is 10).")
    total: Optional[StrictInt] = Field(default=None, description="Total number of records for the request.")
    __properties: ClassVar[List[str]] = ["page", "limit", "total"]

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
    }


    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        # TODO: pydantic v2: use .model_dump_json(by_alias=True, exclude_unset=True) instead
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Create an instance of Metadata from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        _dict = self.model_dump(
            by_alias=True,
            exclude={
            },
            exclude_none=True,
        )
        return _dict

    @classmethod
    def from_dict(cls, obj: Dict) -> Self:
        """Create an instance of Metadata from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "page": obj.get("page"),
            "limit": obj.get("limit"),
            "total": obj.get("total")
        })
        return _obj




class DocumentsList(BaseModel):
    """
    DocumentsList
    """ # noqa: E501
    metadata: Optional[Metadata] = None
    hits: Optional[List[Document]] = None
    __properties: ClassVar[List[str]] = ["metadata", "hits"]

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
    }


    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        # TODO: pydantic v2: use .model_dump_json(by_alias=True, exclude_unset=True) instead
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Create an instance of DocumentsList from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        _dict = self.model_dump(
            by_alias=True,
            exclude={
            },
            exclude_none=True,
        )
        # override the default output from pydantic by calling `to_dict()` of metadata
        if self.metadata:
            _dict['metadata'] = self.metadata.to_dict()
        # override the default output from pydantic by calling `to_dict()` of each item in hits (list)
        _items = []
        if self.hits:
            for _item in self.hits:
                if _item:
                    _items.append(_item.to_dict())
            _dict['hits'] = _items
        return _dict

    @classmethod
    def from_dict(cls, obj: Dict) -> Self:
        """Create an instance of DocumentsList from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "metadata": Metadata.from_dict(obj.get("metadata")) if obj.get("metadata") is not None else None,
            "hits": [Document.from_dict(_item) for _item in obj.get("hits")] if obj.get("hits") is not None else None
        })
        return _obj




class Document(BaseModel):
    """
    Document
    """ # noqa: E501
    uid: StrictStr = Field(description="Web of Science Unique Identifier")
    title: Optional[StrictStr] = Field(default=None, description="Document title")
    types: Optional[List[StrictStr]] = Field(default=None, description="Normalized Document Types")
    source_types: Optional[List[StrictStr]] = Field(default=None, description="Source Document Types", alias="sourceTypes")
    source: Optional[DocumentSource] = None
    names: Optional[DocumentNames] = None
    links: Optional[DocumentLinks] = None
    citations: Optional[List[DocumentCitationsInner]] = Field(default=None, description="Times Cited")
    identifiers: Optional[DocumentIdentifiers] = None
    keywords: Optional[DocumentKeywords] = None
    __properties: ClassVar[List[str]] = ["uid", "title", "types", "sourceTypes", "source", "names", "links", "citations", "identifiers", "keywords"]

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
    }


    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        # TODO: pydantic v2: use .model_dump_json(by_alias=True, exclude_unset=True) instead
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Create an instance of Document from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        _dict = self.model_dump(
            by_alias=True,
            exclude={
            },
            exclude_none=True,
        )
        # override the default output from pydantic by calling `to_dict()` of source
        if self.source:
            _dict['source'] = self.source.to_dict()
        # override the default output from pydantic by calling `to_dict()` of names
        if self.names:
            _dict['names'] = self.names.to_dict()
        # override the default output from pydantic by calling `to_dict()` of links
        if self.links:
            _dict['links'] = self.links.to_dict()
        # override the default output from pydantic by calling `to_dict()` of each item in citations (list)
        _items = []
        if self.citations:
            for _item in self.citations:
                if _item:
                    _items.append(_item.to_dict())
            _dict['citations'] = _items
        # override the default output from pydantic by calling `to_dict()` of identifiers
        if self.identifiers:
            _dict['identifiers'] = self.identifiers.to_dict()
        # override the default output from pydantic by calling `to_dict()` of keywords
        if self.keywords:
            _dict['keywords'] = self.keywords.to_dict()
        return _dict

    @classmethod
    def from_dict(cls, obj: Dict) -> Self:
        """Create an instance of Document from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "uid": obj.get("uid"),
            "title": obj.get("title"),
            "types": obj.get("types"),
            "sourceTypes": obj.get("sourceTypes"),
            "source": DocumentSource.from_dict(obj.get("source")) if obj.get("source") is not None else None,
            "names": DocumentNames.from_dict(obj.get("names")) if obj.get("names") is not None else None,
            "links": DocumentLinks.from_dict(obj.get("links")) if obj.get("links") is not None else None,
            "citations": [DocumentCitationsInner.from_dict(_item) for _item in obj.get("citations")] if obj.get("citations") is not None else None,
            "identifiers": DocumentIdentifiers.from_dict(obj.get("identifiers")) if obj.get("identifiers") is not None else None,
            "keywords": DocumentKeywords.from_dict(obj.get("keywords")) if obj.get("keywords") is not None else None
        })
        return _obj

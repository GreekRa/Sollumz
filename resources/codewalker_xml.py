"""Manages reading/writing Codewalker XML files"""
from mathutils import Vector, Quaternion
from abc import abstractmethod, ABC as AbstractClass, abstractclassmethod, abstractstaticmethod
from dataclasses import dataclass
from typing import Any
from xml.etree import ElementTree as ET

"""Custom indentation to get elements like <VerticesProperty /> to output nicely"""
def indent(elem: ET.Element, level=0):
    amount = "  "
    i = "\n" + level*amount
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + amount
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

        # Indent innertext of elements on new lines. Used in cases like <VerticesProperty />
        if elem.text and len(elem.text.strip()) > 0 and elem.text.find('\n') != -1:
            lines = elem.text.strip().split('\n')
            for index, line in enumerate(lines):
                lines[index] = ((level + 1) * amount) + line
            elem.text = '\n' + '\n'.join(lines) + i

"""Determine if a string is a bool, int, or float"""
def get_str_type(value: str):
    if isinstance(value, str):
        if value.lower() == 'true' or value.lower() == 'false':
            return bool(value)
        
        try:
            return int(value)
        except:
            pass
        try:
            return float(value)
        except:
            pass
        
    return value

class Element(AbstractClass):
    """Abstract XML element to base all other XML elements off of"""
    @property
    @abstractmethod
    def tag_name(self):
        raise NotImplementedError

    @classmethod
    def read_value_error(cls, element):
        raise ValueError(f"Invalid XML element '<{element.tag} />' for type '{cls.__name__}'!")

    """Convert ET.Element object to Element"""
    @abstractclassmethod
    def from_xml(cls, element: ET.Element):
        raise NotImplementedError
    
    """Convert object to ET.Element object"""
    @abstractmethod
    def to_xml(self):
        raise NotImplementedError
    
    """Read XML from filepath"""
    @classmethod
    def from_xml_file(cls, filepath):
        elementTree = ET.ElementTree()
        elementTree.parse(filepath)
        return cls.from_xml(elementTree.getroot())

    
    """Write object as XML to filepath"""
    def write_xml(self, filepath):
        element = self.to_xml()
        indent(element)
        elementTree = ET.ElementTree(element)
        # ET.indent(element)
        elementTree.write(filepath, encoding="UTF-8", xml_declaration=True)


class ElementTree(Element):
    """XML element that contains children defined by it's properties"""

    """Convert ET.Element object to ElementTree"""
    @classmethod
    def from_xml(cls: Element, element: ET.Element):
        new = cls()

        for prop_name, obj_element in vars(new).items():
            if isinstance(obj_element, Element):
                child = element.find(obj_element.tag_name)
                if child != None and obj_element.tag_name == child.tag:
                    # Add element to object if tag is defined in class definition
                    setattr(new, prop_name, type(obj_element).from_xml(child))
            elif isinstance(obj_element, AttributeProperty):
                # Add attribute to element if attribute is defined in class definition
                if obj_element.name in element.attrib and new.tag_name == element.tag:
                    obj_element.value = element.get(obj_element.name)

        return new

    
    """Convert ElementTree to ET.Element object"""
    def to_xml(self):
        root = ET.Element(self.tag_name)
        for child in vars(self).values():
            if isinstance(child, Element):
                root.append(child.to_xml())
            elif isinstance(child, AttributeProperty):
                root.set(child.name, str(child.value))

        return root

    def __getattribute__(self, key: str, onlyValue: bool=True):
        obj = None
        # Try and see if key exists
        try:
            obj = object.__getattribute__(self, key)
            if isinstance(obj, (ElementProperty, AttributeProperty)) and onlyValue:
                # If the property is an ElementProperty or AttributeProperty, and onlyValue is true, return just the value of the Element property
                return obj.value
            else:
                return obj
        except AttributeError:
            # Key doesn't exist, return None
            return None
    
    def __setattr__(self, name: str, value) -> None:
        # Get the full object
        obj = self.__getattribute__(name, False)
        if obj and isinstance(obj, (ElementProperty, AttributeProperty)) and not isinstance(value, (ElementProperty, AttributeProperty)):
            # If the object is an ElementProperty or AttributeProperty, set it's value
            obj.value = value
            super().__setattr__(name, obj)
        else:
            super().__setattr__(name, value)

    def get_element(self, key):
        obj = self.__getattribute__(key, False)

        if isinstance(obj, ElementProperty):
            return obj
    

@dataclass
class AttributeProperty:
    name: str
    _value: Any

    @property
    def value(self):
        return get_str_type(self._value)
    
    @value.setter
    def value(self, value):
        self._value = value

class ElementProperty(Element, AbstractClass):
    @property
    @abstractmethod
    def value_types(self):
        raise NotImplementedError
    
    tag_name = None

    def __init__(self, tag_name: str, value: value_types):
        super().__init__()
        self.tag_name = tag_name
        if value and not isinstance(value, self.value_types):
            raise TypeError(f'Value of {type(self).__name__} must be one of {self.value_types}, not {type(value)}!')
        self.value = value

class TextProperty(ElementProperty):
    value_types = (str)

    '''default = Name ?'''
    def __init__(self, tag_name: str = 'Name', value = None):
        super().__init__(tag_name, value or "")

    @staticmethod
    def from_xml(element: ET.Element):
        return TextProperty(element.tag, element.text)#.strip())

    def to_xml(self):
        return ET.Element(self.tag_name, text = self.value)


class VectorProperty(ElementProperty):
    value_types = (Vector)

    def __init__(self, tag_name: str, value = None):
        super().__init__(tag_name, value or Vector((0, 0, 0)))

    @staticmethod
    def from_xml(element: ET.Element):
        if not all(x in element.attrib.keys() for x in ['x', 'y', 'z']):
            return VectorProperty.read_value_error(element)

        return VectorProperty(element.tag, Vector((float(element.get('x')), float(element.get('y')), float(element.get('z')))))

    def to_xml(self):
        return ET.Element(self.tag_name, attrib={'x': str(self.value.x), 'y': str(self.value.y), 'z': str(self.value.z)})
    

class QuaternionProperty(ElementProperty):
    value_types = (Quaternion)

    def __init__(self, tag_name: str, value = None):
        super().__init__(tag_name, value or Quaternion((0, 0, 0), 1))

    @staticmethod
    def from_xml(element: ET.Element):
        if not all(x in element.attrib.keys() for x in ['x', 'y', 'z', 'w']):
            QuaternionProperty.read_value_error(element)

        return QuaternionProperty(element.tag, Quaternion((float(element.get('x')), float(element.get('y')), float(element.get('z'))), float(element.get('w'))))

    def to_xml(self):
        return ET.Element(self.tag_name, attrib={'x': str(self.value.x), 'y': str(self.value.y), 'z': str(self.value.z), 'w': str(self.value.w)})


class ListProperty(ElementProperty, AbstractClass):
    """Holds a list value. List can only contain values of one type."""

    value_types = (list)
    
    @property
    @abstractmethod
    def list_type(self) -> Element:
        raise NotImplementedError

    def __init__(self, tag_name: str, value = None):
        super().__init__(tag_name, value or [])
    

    @classmethod
    def from_xml(cls, element: ET.Element):
        new = cls(element.tag)
        children = element.findall(new.list_type.tag_name)

        for child in children:
            new.value.append(new.list_type.from_xml(child))
        return new


    def to_xml(self):
        element = ET.Element(self.tag_name)
        for item in self.value:
            if isinstance(item, self.list_type):
                element.append(item.to_xml())
            else:
                raise TypeError(f"{type(self).__name__} can only hold objects of type '{self.list_type.__name__}', not '{type(item)}'")

        return element


class VerticesProperty(ElementProperty):
    value_types = (list)

    def __init__(self, tag_name: str = 'Vertices', value = None):
        super().__init__(tag_name, value or [])

    @staticmethod
    def from_xml(element: ET.Element):
        new = VerticesProperty(element.tag, [])
        text = element.text.strip().split('\n')
        if len(text) > 0:
            for line in text:
                coords = line.strip().split(',')
                if not len(coords) == 3:
                    return VerticesProperty.read_value_error(element)

                new.value.append(Vector((float(coords[0]), float(coords[1]), float(coords[2]))))
        
        return new


    def to_xml(self):
        element = ET.Element(self.tag_name)
        element.text = '\n'
        for vertex in self.value:
            # Should be a list of Vectors
            if not isinstance(vertex, Vector):
                raise TypeError(f"VerticesProperty can only contain Vector objects, not '{type(self.value)}'!")
            for index, component in enumerate(vertex):
                element.text += str(component)
                if index < len(vertex) - 1:
                    element.text += ', '
            element.text += '\n'

        return element


class FlagsProperty(ElementProperty):
    value_types = (list)

    def __init__(self, tag_name: str = 'Flags', value = None):
        super().__init__(tag_name, value or [])

    @staticmethod
    def from_xml(element: ET.Element):
        new = FlagsProperty(element.tag, [])
        if element.text and len(element.text.strip()) > 0:
            text = element.text.replace(' ', '').split(',')
            if not len(text) > 0:
                return FlagsProperty.read_value_error(element)

            for flag in text:
                new.value.append(flag)
        
        return new


    def to_xml(self):
        element = ET.Element(self.tag_name)
        for item in self.value:
            # Should be a list of strings
            if not isinstance(item, str):
                return TypeError('FlagsProperty can only contain str objects!')

        if len(self.value) > 0:
            element.text = ', '.join(self.value)
        return element


class ValueProperty(ElementProperty):
    value_types = (int, str, bool, float)

    def __init__(self, tag_name: str, value):
        super().__init__(tag_name, value)

    @staticmethod
    def from_xml(element: ET.Element):
        if not 'value' in element.attrib:
            ValueError.read_value_error(element)

        return ValueProperty(element.tag, get_str_type(element.get('value')))

    def to_xml(self):
        return ET.Element(self.tag_name, attrib={'value': str(self.value)})
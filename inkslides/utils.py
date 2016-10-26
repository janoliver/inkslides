import re

nsmap = {
    'svg': 'http://www.w3.org/2000/svg',
    'inkscape': 'http://www.inkscape.org/namespaces/inkscape',
    'sodipodi': 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd'
}


def strip_ns(n):
    pattern = "\{(%s)\}" % "|".join([re.escape(x) for x in nsmap.values()])
    return re.sub(pattern, "", n)


def ns_join(tag, namespace):
    """
    This function generates a {namespace}tag string out of a
    namespace keyword and the tagname.
    """
    return '{%s}%s' % (nsmap[namespace], tag)


def get_attr(el, attr, ns='inkscape'):
    # Get an attribute value of an lxml element "el"
    return el.attrib.get(ns_join(attr, ns), False)


def is_layer(group):
    group_attrib = ns_join('groupmode', 'inkscape')
    return strip_ns(group.tag) == 'g' and group_attrib in group.attrib and group.attrib[group_attrib] == 'layer'


def is_text(group):
    group_attrib = ns_join('groupmode', 'inkscape')
    return strip_ns(group.tag) == 'text' and group_attrib in group.attrib and group.attrib[group_attrib] == 'layer'


def is_content_description(lines):
    return len(lines) > 0 and not lines[0].text == None and lines[0].text.strip() == '#content#'


def get_label(elem):
    return elem.attrib[ns_join('label', 'inkscape')]


def get_all_layers(document):
    ret = {}
    for l in document.xpath('//svg:g[@inkscape:groupmode="layer"]', namespaces=nsmap):
        ret[get_attr(l, 'label')] = l
    return ret


def hide_all_layers(document):
    layers = get_all_layers(document)
    for l in layers.values():
        styles = get_styles(l)
        styles['display'] = 'none'
        # styles['opacity'] = '1.0'
        set_styles(l, styles)


def get_styles(el):
    # Get a dict of the content of the style="a:b;c:d" attribute

    items = get_attr(el, 'style', 'svg')
    if not items:
        return dict()
    return dict(item.split(':') for item in items.split(';'))


def set_styles(el, styles):
    # Set the style="" attribute from a dict.

    s = ";".join(sorted(["{}:{}".format(k, v) for k, v in styles.items()]))
    el.attrib['style'] = s


def show_layer(layer):
    """
    Make a layer visible by setting the style= "display:inline"
    attribute.
    """
    styles = get_styles(layer)
    styles['display'] = 'inline'
    # styles['opacity'] = str(opacity)
    set_styles(layer, styles)

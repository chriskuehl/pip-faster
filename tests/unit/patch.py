from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import pip_faster as P


def test_sentinel():
    wat = P.Sentinel('wat')
    assert wat is wat
    assert wat is not None
    assert repr(wat) == '<Sentinel: wat>'


def test_patch():
    d = {1: 1, 2: 2, 3: 3}
    patches = {2: 3, 3: P.patch.DELETE, 4: 4}.items()
    orig = P.patch(d, patches)

    assert d == {1: 1, 2: 3, 4: 4}
    assert orig == {2: 2, 3: 3, 4: P.patch.DELETE}


def test_patched():
    d = {1: 1, 2: 2, 3: 3}
    patches = {2: 3, 3: P.patch.DELETE, 4: 4}

    before = d.copy()
    with P.patched(d, patches) as orig:
        assert d == {1: 1, 2: 3, 4: 4}
        assert orig == {2: 2, 3: 3, 4: P.patch.DELETE}

    assert d == before

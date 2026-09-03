# Raw HTML in st.markdown is fragile in two specific ways

`pages/4_How_RIM_Works.py` and `utils/theme.py` build long `st.markdown(...,
unsafe_allow_html=True)` blocks. Two traps, both of which fail *silently* --
nothing raises, the page just renders less than you wrote.

## A blank line ends the block

Streamlit runs the string through a Markdown renderer before the HTML reaches
the page, and a blank line closes the current HTML block. Everything after it in
that string is discarded or rendered as literal text.

Bitten twice:

- 2026-09-01, an inline `<svg>` with a blank line in it lost its second half.
- 2026-09-03, a `<pre>` holding a JSON example with a blank line between two
  entries silently dropped the rest of the section.

Keep raw HTML blocks free of blank lines. A quick check:

```python
for m in re.finditer(r'<pre[^>]*>(.*?)</pre>', source, re.S):
    assert '\n\n' not in m.group(1)
```

## A wrapper `<div>` does not span two calls

Opening a container in one `st.markdown` and closing it in the next does not
nest the elements Streamlit renders in between. Each call is its own block.

## `<pre>` is not worth fighting

Even with no blank line, a `<pre class="...">` of indented JSON did not survive
the Markdown pass -- the class was gone and no `<pre>` element appeared. Use
`st.code(text, language="json")` instead: a real Streamlit element, styled for
free, and it can be fed from the same constant the app actually uses so the
documentation cannot drift from the thing it documents. That is what
`pages/4_How_RIM_Works.py` now does with
`utils.custom_options_ui.EXAMPLE`.

Prefer a native element to hand-rolled HTML whenever one exists.

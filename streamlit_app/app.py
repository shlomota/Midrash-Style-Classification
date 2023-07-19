import joblib
import streamlit as st
import re
import eli5
from bs4 import BeautifulSoup

st.set_page_config(layout='wide')

CSS_STREAMLIT_MARGIN_HACK = """
<style>
.reportview-container .main .block-container {
    max-width: 1200px;
    padding-top: 5rem;
    padding-right: 2rem;
    padding-left: 2rem;
    margin: auto;
}
</style>
"""

CSS_HIGHLIGHT = """<style>
    table.eli5-weights tr:hover {
        filter: brightness(85%);
    }

    .highlight {
        background-color: #00FF00;
    }
</style>"""

JS_HIGHLIGHT_CODE_BLOCK = """<script>
    window.onload = function() {
        var tds = document.querySelectorAll("td");
        var maxProb = -1;
        var maxProbElem = null;
        for (var i = 0; i < tds.length; i++) {
			var bTags = tds[i].querySelectorAll("b");
			if (bTags.length < 2) continue; // If there are less than 2 <b> tags, skip to the next iteration

			var prob = parseFloat(bTags[1].innerText);


            if (prob > maxProb) {
                maxProb = prob;
                if (maxProbElem != null) {
                    maxProbElem.classList.remove("highlight");
                }
                maxProbElem = tds[i];
                maxProbElem.classList.add("highlight");
            }
        }

		let paragraphs = Array.from(document.getElementsByTagName('p'));
		let filteredParagraphs = paragraphs.filter(p => p.textContent.includes("(probability"));
		
		let probabilities = filteredParagraphs.map(p => parseFloat(p.textContent.match(/(\d+(?:\.\d+)?)/)[0]));

		let maxProbability = Math.max(...probabilities);
		let maxProbabilityIndex = probabilities.findIndex(p => p === maxProbability);

		filteredParagraphs[maxProbabilityIndex].classList.add("highlight");
    }
</script>"""

def do_highlight_highest(html):
    soup = BeautifulSoup(html, 'html.parser')

    # Select all <td> tags
    tds = soup.find_all('td')

    max_prob = -1
    max_prob_elem = None
    for td in tds:
        b_tags = td.find_all('b')
        if len(b_tags) < 2:
            continue

        prob = float(b_tags[1].text)
        if prob > max_prob:
            max_prob = prob
            if max_prob_elem is not None:
                max_prob_elem['class'] = max_prob_elem.get('class', [])
                if 'highlight' in max_prob_elem['class']:
                    max_prob_elem['class'].remove('highlight')
            max_prob_elem = td
            if 'class' in max_prob_elem:
                max_prob_elem['class'].append('highlight')
            else:
                max_prob_elem['class'] = ['highlight']

    # Select paragraphs
    paragraphs = soup.find_all('p')
    filtered_paragraphs = [p for p in paragraphs if "(probability" in p.text]

    probabilities = [float(re.search(r"(\d+(?:\.\d+)?)", p.text)[0]) for p in filtered_paragraphs]

    max_probability = max(probabilities)
    max_probability_index = probabilities.index(max_probability)

    filtered_paragraphs[max_probability_index]['class'] = filtered_paragraphs[max_probability_index].get('class', []) + ['highlight']

    # convert soup object back to string
    html = str(soup)
    return "%s\n%s" % (CSS_HIGHLIGHT, html)

def filter_non_hebrew(text):
    # The Unicode range for Hebrew is U+0590 to U+05FF.
    # The Unicode range for Hebrew diacritical marks is U+0591 to U+05BD, U+05BF, U+05C1, U+05C2, U+05C4, U+05C5, U+05C7.
    # So, the Unicode range for Hebrew letters without diacritical marks is U+05D0 to U+05EA.
    hebrew_text = re.sub(r'[^\u05D0-\u05EA ]', '', text)
    return hebrew_text

def clean_text(text):
    # Replace multiple newlines (possibly with spaces in between) with a single newline
    cleaned_text = re.sub(r'\s*\n\s*', '\n', text)
    return cleaned_text

def remove_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def contains_hebrew(text):
    return bool(re.search('[\u0590-\u05FF]', text))

def mark_hebrew_paragraphs(html):
    soup = BeautifulSoup(html, 'html.parser')

    for p in soup.find_all('p'):
        if contains_hebrew(p.get_text()):
            p['class'] = p.get('class', []) + ['hebrew']

    return str(soup)

st.title("Style detection")

labels = ["Mishnah", "Halacha", "Yerushalmi", "Bavli", "Aggadah", "Tanchuma"]#, "Unknown"]
mode = "normal"
# mode = "morph"

model = joblib.load(f"style_normal_logistic_1_3.pkl")
vec = joblib.load(f"style_normal_logistic_vec_1_3.pkl")


default_text = "וידבר ה' אל משה במדבר סיני, זהו שאמר הכתוב. משפטיך תהום רבה, אמר רבי מאיר משל את הצדיקים בדירתן ואת הרשעים בדירתן, משל את הצדיקים בדירתן. במרעה טוב ארעה אתם ובהרי מרום ישראל יהיה נוהם, ומשל את הרשעים בדירתן. כה אמר ה' אלהים ביום רדתו שאולה האבלתי כסתי עליו את"

label = "Enter a paragraph here"

#inp_text = st.text_input(label, value=default_text)
st.markdown("""
<style>
textarea {
  unicode-bidi:bidi-override;
  direction: RTL;
}
</style>
    """, unsafe_allow_html=True)


st.markdown("""
<style>
.hebrew {
  unicode-bidi:bidi-override;
  direction: RTL;
  font-size: 20px;
  font-family: 'David Libre';
}
</style>
    """, unsafe_allow_html=True)

# Use it like this:
inp_text = st.text_area(label, value=default_text)
inp_text_without_tags = remove_html_tags(inp_text)
filtered_text = filter_non_hebrew(inp_text_without_tags)

ex = eli5.explain_prediction(model, filtered_text, vec=vec, target_names=labels)
exhtml = eli5.formatters.html.format_as_html(ex)
exhtml = clean_text(exhtml)
exhtml = do_highlight_highest(exhtml)
exhtml = mark_hebrew_paragraphs(exhtml)
res = exhtml.replace("eli5-weights", "eli5weights").replace("\n", " ")
st.markdown(res, unsafe_allow_html=True)
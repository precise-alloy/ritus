let nextCardId = 0;

export function card({ heading, headingLevel = 2, body, href, className = '' }) {
  const section = document.createElement('section');
  section.className = ['card', className].filter(Boolean).join(' ');

  const level = Math.min(Math.max(Number(headingLevel) || 2, 2), 6);
  const title = document.createElement(`h${level}`);
  const id = `card-heading-${nextCardId}`;
  nextCardId += 1;
  title.id = id;

  if (href) {
    const link = document.createElement('a');
    link.href = href;
    link.textContent = heading;
    title.append(link);
  } else {
    title.textContent = heading;
  }

  section.setAttribute('aria-labelledby', id);
  section.append(title);

  if (Array.isArray(body)) {
    section.append(...body);
  } else if (body instanceof Node) {
    section.append(body);
  } else if (body) {
    const paragraph = document.createElement('p');
    paragraph.textContent = String(body);
    section.append(paragraph);
  }

  return section;
}

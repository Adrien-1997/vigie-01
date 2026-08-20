import { monogram, sourceLogo } from "../lib/logos";

/** Marque du média, dans un cartouche de taille fixe. Le fond clair est constant, en clair comme
 *  en sombre : les favicons sont dessinés pour un fond blanc, et beaucoup sont des glyphes sombres
 *  sur transparent — posés directement sur la surface sombre, ils disparaissent. */
export function SourceLogo({ source }: { source: string }) {
  const url = sourceLogo(source);

  if (!url) {
    return (
      <span className="logo logo-mono" title={source} aria-hidden>
        {monogram(source)}
      </span>
    );
  }

  return (
    <span className="logo" title={source}>
      <img src={url} alt="" loading="lazy" decoding="async" />
    </span>
  );
}

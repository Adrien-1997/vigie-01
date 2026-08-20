const base = {
  width: 13,
  height: 13,
  viewBox: "0 0 16 16",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.7,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

export const SearchIcon = () => (
  <svg {...base} width={14} height={14}>
    <circle cx="7" cy="7" r="4.5" />
    <path d="M10.5 10.5 14 14" />
  </svg>
);

export const CheckIcon = () => (
  <svg {...base}>
    <path d="M3 8.5 6.2 11.5 13 4.5" />
  </svg>
);

export const AlertIcon = () => (
  <svg {...base}>
    <path d="M8 2.2 14.5 13.5h-13z" />
    <path d="M8 6.6v3" />
    <path d="M8 11.7h.01" />
  </svg>
);

export const PinIcon = () => (
  <svg {...base} width={11} height={11}>
    <path d="M8 14.5s5-4.6 5-8a5 5 0 1 0-10 0c0 3.4 5 8 5 8Z" />
    <circle cx="8" cy="6.4" r="1.8" />
  </svg>
);

export const RefreshIcon = () => (
  <svg {...base} width={14} height={14}>
    <path d="M14 3v4h-4" />
    <path d="M13.3 7A5.6 5.6 0 1 0 13 10.4" />
  </svg>
);

export const ListIcon = () => (
  <svg {...base} width={14} height={14}>
    <path d="M6 4h8M6 8h8M6 12h8M2.5 4h.01M2.5 8h.01M2.5 12h.01" />
  </svg>
);

export const MapIcon = () => (
  <svg {...base} width={14} height={14}>
    <path d="M1.5 4 6 2.2l4 1.8 4.5-1.8v9.6L10 13.6l-4-1.8-4.5 1.8z" />
    <path d="M6 2.2v9.6M10 4v9.6" />
  </svg>
);

export const TableIcon = () => (
  <svg {...base} width={14} height={14}>
    <rect x="1.8" y="2.8" width="12.4" height="10.4" rx="1.4" />
    <path d="M1.8 6.4h12.4M6.6 6.4v6.8" />
  </svg>
);

export const SunIcon = () => (
  <svg {...base} width={15} height={15}>
    <circle cx="8" cy="8" r="3.1" />
    <path d="M8 1v1.6M8 13.4V15M15 8h-1.6M2.6 8H1M12.9 3.1l-1.1 1.1M4.2 11.8l-1.1 1.1M12.9 12.9l-1.1-1.1M4.2 4.2 3.1 3.1" />
  </svg>
);

export const ThreadIcon = () => (
  <svg {...base} width={12} height={12}>
    <circle cx="4" cy="4" r="2" />
    <circle cx="4" cy="12" r="2" />
    <circle cx="12" cy="8" r="2" />
    <path d="M5.6 5.1 10.4 7.2M5.6 10.9 10.4 8.8" />
  </svg>
);

export const MoonIcon = () => (
  <svg {...base} width={15} height={15}>
    <path d="M13.5 9.4A5.9 5.9 0 0 1 6.6 2.5a5.9 5.9 0 1 0 6.9 6.9Z" />
  </svg>
);

export const CloseIcon = () => (
  <svg {...base} width={11} height={11}>
    <path d="M4 4l8 8M12 4l-8 8" />
  </svg>
);

export const ArrowUpIcon = () => (
  <svg {...base} width={14} height={14}>
    <path d="M8 13V3.5" />
    <path d="M3.8 7.4 8 3.2l4.2 4.2" />
  </svg>
);

export const FilterIcon = () => (
  <svg {...base} width={14} height={14}>
    <path d="M2 3.5h12l-4.6 5.2v4.4l-2.8 1.4V8.7z" />
  </svg>
);

/** Chevron d'en-tête de colonne triable. `dir` porte le sens, jamais la seule couleur. */
export const SortIcon = ({ dir }: { dir: "asc" | "desc" | null }) => (
  <svg {...base} width={11} height={11} className="sort-icon">
    <path d="M8 3v10" opacity={dir ? 1 : 0.35} />
    {dir === "desc" ? <path d="M4.4 9.4 8 13l3.6-3.6" /> : <path d="M4.4 6.6 8 3l3.6 3.6" opacity={dir ? 1 : 0.35} />}
  </svg>
);

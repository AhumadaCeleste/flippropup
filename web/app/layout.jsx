import "./globals.css";
import localFont from "next/font/local";

// Plus Jakarta Sans (SIL Open Font License), incluida en el proyecto.
const jakarta = localFont({
  src: [
    { path: "./fonts/plus-jakarta-sans-latin-500-normal.woff2", weight: "500", style: "normal" },
    { path: "./fonts/plus-jakarta-sans-latin-600-normal.woff2", weight: "600", style: "normal" },
    { path: "./fonts/plus-jakarta-sans-latin-700-normal.woff2", weight: "700", style: "normal" },
    { path: "./fonts/plus-jakarta-sans-latin-800-normal.woff2", weight: "800", style: "normal" },
  ],
  variable: "--font-jakarta",
});

export const metadata = {
  title: "Flip PropUp",
  description: "Detectá propiedades subvaluadas antes que el mercado.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="es-AR" className={jakarta.variable}>
      <body>{children}</body>
    </html>
  );
}

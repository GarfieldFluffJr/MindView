import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MindView",
  description: "MindView Application",
  icons: {
    icon: "/brainstorm.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}

export const metadata = {
  title: "AI-Access OS | Universal AI Setup",
  description: "Configure your universal AI assistant device settings.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}

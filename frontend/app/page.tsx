import { Nav } from "./_components/Nav";
import { Hero } from "./_components/Hero";
import { Differentiators } from "./_components/Differentiators";
import { HowItWorks } from "./_components/HowItWorks";
import { InputStrip } from "./_components/InputStrip";
import { TrustBand } from "./_components/TrustBand";
import { FooterCTA } from "./_components/FooterCTA";

export default function Home() {
  return (
    <main>
      <Nav />
      <Hero />
      <Differentiators />
      <HowItWorks />
      <InputStrip />
      <TrustBand />
      <FooterCTA />
    </main>
  );
}

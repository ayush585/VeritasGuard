# Frontend Design Parity Checklist

This checklist tracks manual parity against the Figma visual language while preserving VeritasGuard IA.

## Global System
- [x] Color tokens upgraded for civic command tone (`tokens.css`)
- [x] Typography stack includes Space Grotesk + Indic script-safe fallbacks
- [x] Unified radius/spacing/shadow scale added as CSS variables
- [x] Reduced-motion behavior preserved
- [x] Brand mark + wordmark applied in app shell and favicon

## Route: `/` Landing Narrative
- [x] Hero with high-trust visual treatment and clear CTA
- [x] Problem -> intervention -> impact strip emphasized
- [x] 8-agent pipeline block retained
- [x] Channel cards styled as product pathways (WhatsApp / Command / Institutional API)
- [x] Motion entrance sequence via GSAP timeline

## Route: `/verify` Command Center
- [x] Three-column desktop layout with responsive tablet/mobile fallback
- [x] Input module with text/image mode and sample selector
- [x] Sticky action controls on mobile
- [x] Pipeline phase rail with state-aware badges and latency metrics
- [x] Verdict panel with confidence bar and deterministic override banner
- [x] Evidence panel with provider/completeness badges and warning normalization
- [x] Consensus panel with votes table and weighted meters
- [x] Evidence graph panel supports backend schema (`support_edges`, `contradiction_edges`, `final_decision_path`)
- [x] Debug drawer supports protected endpoint fallback messaging

## Robustness and Demo Safety
- [x] Object-safe rendering guards in UI for uncertain payload shapes
- [x] No blank panel states; all panels render fallback helper messages
- [x] Mojibake cleanup for multilingual sample inputs
- [x] Debug API now expects admin-key flow from frontend env (`VITE_ADMIN_API_KEY`)

## Pending (post-MCP integration)
- [ ] Extract exact Figma spacing/typography values via MCP once server is connected
- [ ] Replace approximate gradients with exact Figma token values
- [ ] Align iconography and micro-illustrations 1:1 with exported design assets

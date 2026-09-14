// The existing production stream. This is a public identifier, not a secret.
// Set enhancedMeasurementReviewed only after the setup in docs/analytics.md.
export const ANALYTICS_CONFIG = Object.freeze({
  measurementId: 'G-B3FYWYWXTN',
  productionHosts: ['whobuiltmyhome.com', 'www.whobuiltmyhome.com'],
  enhancedMeasurementReviewed: false,
});

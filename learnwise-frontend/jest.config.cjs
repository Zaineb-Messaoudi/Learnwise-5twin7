module.exports = {
  testEnvironment: 'jsdom',
  roots: ['<rootDir>/tests', '<rootDir>/src'],
  setupFilesAfterEnv: ['<rootDir>/tests/setup.js'],
  moduleFileExtensions: ['js', 'jsx'],
  transform: { '^.+\\.[jt]sx?$': 'babel-jest' },
  transformIgnorePatterns: [
    'node_modules/(?!(face-api.js|@mediapipe|pdfjs-dist)/)'
  ],
  moduleNameMapper: { '\\.(css)$': '<rootDir>/tests/styleMock.js' },
}
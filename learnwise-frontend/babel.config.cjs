module.exports = { 
  presets: [
    ['@babel/preset-env', { targets: { node: 'current' }, modules: 'commonjs' }],
    ['@babel/preset-react', { runtime: 'automatic' }]
  ],
  plugins: [
    ['@babel/plugin-transform-modules-commonjs', { allowTopLevelThis: true }],
    function importMetaPlugin() {
      const t = require('@babel/types');
      return {
        visitor: {
          MetaProperty(path) {
            const { node } = path;
            if (node.meta.name === 'import' && node.property.name === 'meta') {
              const mockMeta = t.objectExpression([
                t.objectProperty(t.identifier('env'), t.objectExpression([
                  t.objectProperty(t.identifier('VITE_API_URL'), t.stringLiteral('/api/v1')),
                  t.objectProperty(t.identifier('VITE_API_MODE'), t.stringLiteral('mock')),
                  t.objectProperty(t.identifier('VITE_GOOGLE_CLIENT_ID'), t.stringLiteral('test-google-id')),
                  t.objectProperty(t.identifier('VITE_FACEBOOK_APP_ID'), t.stringLiteral('test-facebook-id')),
                  t.objectProperty(t.identifier('VITE_WS_URL'), t.stringLiteral('ws://localhost'))
                ]))
              ]);
              path.replaceWith(mockMeta);
            }
          }
        }
      };
    }
  ]
}
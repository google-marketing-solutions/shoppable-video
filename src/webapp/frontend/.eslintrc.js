const path = require('path');

module.exports = {
  extends: './node_modules/gts/',
  parserOptions: {
    tsconfigRootDir: __dirname,
    project: [
      path.resolve(__dirname, 'tsconfig.app.json'),
      path.resolve(__dirname, 'tsconfig.spec.json'),
    ],
  },
};

import { defineConfig } from "steiger";
import fsd from "@feature-sliced/steiger-plugin";

export default defineConfig([
  ...fsd.configs.recommended,
  {
    rules: {
      // Пока в приложении одна страница, каждый слайс используется ровно один раз.
      // Вернуть правило, когда страниц станет больше.
      "fsd/insignificant-slice": "off",
    },
  },
]);

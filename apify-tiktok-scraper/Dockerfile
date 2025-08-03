# Use Apify base image with Node.js and Playwright
FROM apify/actor-node-playwright-chrome:18

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production --quiet \
    && npm cache clean --force

# Copy source code
COPY . ./

# Run the scraper
CMD npm start
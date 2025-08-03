# ML Models Directory

This directory contains trained machine learning models for video performance prediction and analytics.

## Structure

```
ml_models/
├── performance/          # Performance prediction models
│   ├── tiktok_model.pkl     # TikTok-specific model
│   ├── instagram_model.pkl  # Instagram-specific model
│   ├── youtube_model.pkl    # YouTube-specific model
│   └── model_metadata.json  # Model metadata and versions
├── trend_analysis/       # Trend analysis models
│   ├── trend_classifier.pkl
│   └── relevance_model.pkl
└── ab_testing/          # A/B testing optimization models
    ├── variant_generator.pkl
    └── experiment_optimizer.pkl
```

## Model Types

### Performance Prediction Models
- **Platform-specific models**: Trained separately for each platform (TikTok, Instagram, YouTube)
- **Multi-output regression**: Predicts multiple metrics (views, engagement rate, scores)
- **Feature engineering**: Uses visual, audio, and metadata features

### Trend Analysis Models
- **Trend classification**: Categorizes trends by type and relevance
- **Relevance scoring**: Matches trends to brand characteristics
- **Growth prediction**: Forecasts trend lifecycle and decay

### A/B Testing Models
- **Variant generation**: AI-powered creation of test variants
- **Experiment optimization**: Determines optimal test parameters
- **Statistical analysis**: Automated significance testing

## Model Training

Models are retrained periodically using the latest performance data:

1. **Data Collection**: Gather recent video performance metrics
2. **Feature Engineering**: Extract visual, audio, and contextual features
3. **Model Training**: Train platform-specific models
4. **Validation**: Cross-validate on held-out test sets
5. **Deployment**: Replace existing models if performance improves

## Model Versioning

Each model includes:
- Version number (semantic versioning)
- Training date and duration
- Performance metrics (accuracy, precision, recall)
- Feature importance scores
- Hyperparameters used

## Usage

Models are automatically loaded by the PerformancePredictor service:

```python
from app.services.analytics.performance_predictor import PerformancePredictor

predictor = PerformancePredictor()
result = await predictor.predict_performance(video_path, platform)
```

## Performance Metrics

Current model performance (updated automatically):

| Platform  | Accuracy | MAE  | R²   | Last Updated |
|-----------|----------|------|------|--------------|
| TikTok    | 0.85     | 8.2  | 0.72 | 2024-12-19   |
| Instagram | 0.82     | 9.1  | 0.68 | 2024-12-19   |
| YouTube   | 0.78     | 10.5 | 0.65 | 2024-12-19   |

## Model Updates

Models are automatically retrained:
- **Daily**: Incremental updates with new data
- **Weekly**: Full retraining with hyperparameter optimization
- **Monthly**: Model architecture review and improvement

## Monitoring

Model performance is continuously monitored:
- Prediction accuracy vs actual results
- Feature drift detection
- Performance degradation alerts
- A/B testing of model versions
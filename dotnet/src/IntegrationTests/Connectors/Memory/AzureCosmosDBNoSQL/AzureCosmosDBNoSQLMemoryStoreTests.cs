﻿// Copyright (c) Microsoft. All rights reserved.

using System;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.SemanticKernel.Connectors.AzureCosmosDBNoSQL;
using Microsoft.SemanticKernel.Memory;
using MongoDB.Driver;
using Xunit;

namespace SemanticKernel.IntegrationTests.Connectors.AzureCosmosDBNoSQL;

/// <summary>
/// Integration tests of <see cref="AzureCosmosDBNoSQLMemoryStore"/>.
/// </summary>
public class AzureCosmosDBNoSQLMemoryStoreTests : IClassFixture<AzureCosmosDBNoSQLMemoryStoreTestsFixture>
{
    private const string? SkipReason = "Azure Cosmos DB Account with Vector indexing enabled required";

    private readonly AzureCosmosDBNoSQLMemoryStoreTestsFixture _fixture;

    public AzureCosmosDBNoSQLMemoryStoreTests(AzureCosmosDBNoSQLMemoryStoreTestsFixture fixture)
    {
        this._fixture = fixture;
    }

    [Fact(Skip = SkipReason)]
    public async Task ItCanCreateGetCheckAndDeleteCollectionAsync()
    {
        var collectionName = this._fixture.CollectionName;
        var memoryStore = this._fixture.MemoryStore;

        await memoryStore.CreateCollectionAsync(collectionName);
        var collectionNames = memoryStore.GetCollectionsAsync();

        Assert.True(await collectionNames.ContainsAsync(collectionName));
        Assert.True(await memoryStore.DoesCollectionExistAsync(collectionName));

        await memoryStore.DeleteCollectionAsync(collectionName);
        Assert.False(await memoryStore.DoesCollectionExistAsync(collectionName));
    }

    [Theory(Skip = SkipReason)]
    [InlineData(true)]
    [InlineData(false)]
    public async Task ItCanBatchUpsertGetRemoveAsync(bool withEmbeddings)
    {
        const int Count = 10;
        var collectionName = this._fixture.CollectionName;
        var memoryStore = this._fixture.MemoryStore;
        var records = DataHelper.CreateBatchRecords(Count);

        await memoryStore.CreateCollectionAsync(collectionName);
        var keys = await memoryStore.UpsertBatchAsync(collectionName, records).ToListAsync();
        var actualRecords = await memoryStore
            .GetBatchAsync(collectionName, keys, withEmbeddings: withEmbeddings)
            .ToListAsync();

        Assert.NotNull(keys);
        Assert.NotNull(actualRecords);
        Assert.Equal(keys, actualRecords.Select(obj => obj.Key).ToList());
        Console.WriteLine(actualRecords);

        var actualRecordsOrdered = actualRecords.OrderBy(r => r.Key).ToArray();
        for (int i = 0; i < Count; i++)
        {
            AssertMemoryRecordEqual(
                records[i],
                actualRecordsOrdered[i],
                assertEmbeddingEqual: withEmbeddings
            );
        }

        await memoryStore.RemoveBatchAsync(collectionName, keys);
        var ids = await memoryStore.GetBatchAsync(collectionName, keys).ToListAsync();
        Assert.Empty(ids);

        await memoryStore.DeleteCollectionAsync(collectionName);
    }

    [Theory(Skip = SkipReason)]
    [InlineData(1, false)]
    [InlineData(1, true)]
    [InlineData(5, false)]
    [InlineData(8, false)]
    public async Task ItCanGetNearestMatchesAsync(int limit, bool withEmbeddings)
    {
        var collectionName = this._fixture.CollectionName;
        var memoryStore = this._fixture.MemoryStore;
        var searchEmbedding = DataHelper.VectorSearchTestEmbedding;
        var nearestMatchesExpected = DataHelper.VectorSearchExpectedResults;

        await memoryStore.CreateCollectionAsync(collectionName);
        var keys = await memoryStore.UpsertBatchAsync(collectionName, DataHelper.VectorSearchTestRecords).ToListAsync();

        var nearestMatchesActual = await memoryStore
            .GetNearestMatchesAsync(
                collectionName,
                searchEmbedding,
                limit,
                withEmbeddings: withEmbeddings
            )
            .ToListAsync();

        Assert.NotNull(nearestMatchesActual);
        Assert.Equal(limit, nearestMatchesActual.Count);

        for (int i = 0; i < limit; i++)
        {
            AssertMemoryRecordEqual(
                nearestMatchesExpected[i],
                nearestMatchesActual[i].Item1,
                withEmbeddings
            );
        }

        await memoryStore.DeleteCollectionAsync(collectionName);
    }

    private static void AssertMemoryRecordEqual(
        MemoryRecord expectedRecord,
        MemoryRecord actualRecord,
        bool assertEmbeddingEqual = true
    )
    {
        Assert.Equal(expectedRecord.Key, actualRecord.Key);
        Assert.Equal(expectedRecord.Timestamp, actualRecord.Timestamp);
        Assert.Equal(expectedRecord.Metadata.Id, actualRecord.Metadata.Id);
        Assert.Equal(expectedRecord.Metadata.Text, actualRecord.Metadata.Text);
        Assert.Equal(expectedRecord.Metadata.Description, actualRecord.Metadata.Description);
        Assert.Equal(
            expectedRecord.Metadata.AdditionalMetadata,
            actualRecord.Metadata.AdditionalMetadata
        );
        Assert.Equal(expectedRecord.Metadata.IsReference, actualRecord.Metadata.IsReference);
        Assert.Equal(
            expectedRecord.Metadata.ExternalSourceName,
            actualRecord.Metadata.ExternalSourceName
        );

        if (assertEmbeddingEqual)
        {
            Assert.True(expectedRecord.Embedding.Span.SequenceEqual(actualRecord.Embedding.Span));
        }
        else
        {
            Assert.True(actualRecord.Embedding.Span.IsEmpty);
        }
    }
}
